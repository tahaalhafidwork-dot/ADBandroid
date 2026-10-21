"""Phase 3B tests use a mock provider exclusively; no cloud request is possible."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from . import PROJECT_ROOT  # noqa: F401

from backend.ai_tests import get_ai_provider_factory
from backend.database import Base, get_session
from backend.main import app
from backend.models import AIProviderConfig, AITestRun, DialectTerm, ListingDraft, ProviderRuntimeMetric, SourcePost
from backend.processing.privacy import ACCOUNT_MARKER, PHONE_MARKER, URL_MARKER, redact_personal_data
from backend.processing.schemas import OutputParseError, parse_extraction_output
from backend.providers.base import ProviderFailure, ProviderRequest, ProviderResponse
from backend.seed import seed_provider_configs


def result_payload(**changes):
    value = {
        "category": "for_sale", "property_type": "apartment", "title": "شقة للبيع",
        "description": None, "price": 125000, "currency": "USD", "area_sqm": 140,
        "bedrooms": 3, "bathrooms": 2, "city": "بغداد", "district": "المنصور",
        "complex_name": None, "floor": None, "furnished": None, "confidence": 0.91,
        "uncertain_fields": [], "needs_review": False, "review_notes": [],
    }
    value.update(changes)
    return value


class MockProvider:
    def __init__(self):
        self.calls: list[ProviderRequest] = []
        self.response = ProviderResponse(
            content=json.dumps(result_payload(), ensure_ascii=False), requested_model="kilo-auto/free",
            actual_model="mock/free-model", http_status=200, finish_reason="stop", duration_ms=25,
            input_tokens=50, output_tokens=30, total_tokens=80, actual_cost=None,
            raw_body=json.dumps({"model": "mock/free-model", "safe": True}),
        )
        self.failure: ProviderFailure | None = None

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.calls.append(request)
        if self.failure:
            raise self.failure
        return self.response


class TestPrivacyAndStrictOutput:
    @pytest.mark.parametrize("phone", [
        "0770 123 4567", "+964 770-123-4567", "٠٧٧٠ ١٢٣ ٤٥٦٧", "۰۰۹۶۴ ۷۷۰ ۱۲۳ ۴۵۶۷",
    ])
    def test_iraqi_phone_forms_are_redacted(self, phone):
        output = redact_personal_data("للبيع اتصل " + phone)
        assert PHONE_MARKER in output
        assert phone not in output

    def test_social_identifiers_are_redacted(self):
        source = "https://facebook.com/person.name اسم الحساب: صاحب العقار\n@broker_name Facebook ID: 123456789"
        output = redact_personal_data(source)
        assert URL_MARKER in output
        assert ACCOUNT_MARKER in output
        assert "person.name" not in output and "broker_name" not in output and "123456789" not in output

    @pytest.mark.parametrize("changes", [
        {"category": "for_sale"},
        {"category": "for_rent", "price": 500000, "currency": "IQD"},
        {"category": "real_estate_service", "property_type": None, "price": None, "currency": None},
        {"category": "unclear", "property_type": "unclear", "confidence": 0.25, "needs_review": True},
        {"price": None, "currency": None, "uncertain_fields": ["price"], "needs_review": True},
        {"title": "بيت طابو صرف", "review_notes": ["فهم مصطلح عراقي من القاموس"]},
    ])
    def test_sale_rent_service_ambiguity_price_and_dialect_shapes(self, changes):
        parsed = parse_extraction_output(json.dumps(result_payload(**changes), ensure_ascii=False), "stop")
        assert parsed.category == changes.get("category", "for_sale")

    def test_complete_code_fence_is_accepted_without_repair(self):
        parsed = parse_extraction_output("```json\n" + json.dumps(result_payload()) + "\n```", "stop")
        assert parsed.price == 125000

    @pytest.mark.parametrize("content,finish,kind", [
        ('{"category":"for_sale"', "length", "truncated_json"),
        ("not-json", "stop", "invalid_json"),
        (json.dumps(result_payload(extra_field=True)), "stop", "invalid_schema"),
        (json.dumps(result_payload(price=-1)), "stop", "invalid_schema"),
    ])
    def test_invalid_truncated_and_schema_errors_are_rejected(self, content, finish, kind):
        with pytest.raises(OutputParseError) as raised:
            parse_extraction_output(content, finish)
        assert raised.value.kind == kind


class TestAITestAPI:
    @classmethod
    def setup_class(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        cls.mock = MockProvider()

        def override_session():
            with cls.Session() as session:
                yield session

        def override_factory():
            return lambda _config, _key: cls.mock

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_ai_provider_factory] = override_factory
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setup_method(self):
        self.saved_env = {key: os.environ.get(key) for key in (
            "KILO_API_KEY", "AQARATI_LAB_OFFLINE", "AQARATI_LAB_ENABLE_CLOUD_AI_TEST",
        )}
        os.environ.update({
            "KILO_API_KEY": "test-key-never-sent", "AQARATI_LAB_OFFLINE": "false",
            "AQARATI_LAB_ENABLE_CLOUD_AI_TEST": "true",
        })
        type(self).mock = MockProvider()
        with self.Session.begin() as session:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
            seed_provider_configs(session)
            provider = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == "kilo"))
            provider.is_enabled = True
            provider.request_limit = 20
            post = SourcePost(
                source_identifier="synthetic-1", source_fingerprint="a" * 64, source="synthetic",
                source_url="https://private.example/source", original_text=(
                    "شقة للبيع بالمنصور 140 متر. اتصل ٠٧٧٠ ١٢٣ ٤٥٦٧ "
                    "https://facebook.com/private.owner"
                ), image_urls=["https://private.example/photo.jpg"], category="for_sale",
                processing_status="ok", is_duplicate=False,
            )
            session.add(post)
            session.flush()
            session.add(ListingDraft(
                source_post_id=post.id, listing_type="for_sale", property_type="apartment",
                title="المسودة القديمة", price=100000, currency="USD", city="بغداد",
                review_status="approved", verification_status="verified",
            ))
            session.add(DialectTerm(term="طابو", meaning="سند ملكية", approval_status="approved"))
        self.post_id = 1

    def teardown_method(self):
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _preview(self):
        response = self.client.post("/api/ai-tests/preview", json={"post_id": self.post_id})
        assert response.status_code == 200
        return response.json()

    def _run(self, key="test-run-0001", **changes):
        preview = self._preview()
        payload = {
            "post_id": self.post_id, "preview_fingerprint": preview["preview_fingerprint"],
            "idempotency_key": key, "confirmed_external_send": True,
            "accepted_data_handling": True, "accepted_unknown_cost": True,
        }
        payload.update(changes)
        return self.client.post("/api/ai-tests/run", json=payload)

    def test_preview_redacts_pii_and_reports_guards_without_calling_provider(self):
        preview = self._preview()
        assert preview["ready"] is True
        assert "٠٧٧٠" not in preview["redacted_text"]
        assert "private.owner" not in preview["redacted_text"]
        assert type(self).mock.calls == []

    def test_all_confirmations_and_runtime_guards_are_required(self):
        preview = self._preview()
        denied = self.client.post("/api/ai-tests/run", json={
            "post_id": self.post_id, "preview_fingerprint": preview["preview_fingerprint"],
            "idempotency_key": "denied-run", "confirmed_external_send": False,
            "accepted_data_handling": True, "accepted_unknown_cost": True,
        })
        assert denied.status_code == 422
        os.environ.pop("KILO_API_KEY")
        no_key = self.client.post("/api/ai-tests/run", json={
            "post_id": self.post_id, "preview_fingerprint": preview["preview_fingerprint"],
            "idempotency_key": "no-key-run", "confirmed_external_send": True,
            "accepted_data_handling": True, "accepted_unknown_cost": True,
        })
        assert no_key.status_code == 409
        assert type(self).mock.calls == []

    def test_offline_and_cloud_kill_switches_block_before_provider(self):
        os.environ["AQARATI_LAB_OFFLINE"] = "true"
        os.environ["AQARATI_LAB_ENABLE_CLOUD_AI_TEST"] = "false"
        preview = self._preview()
        failed = {guard["key"] for guard in preview["guards"] if not guard["ok"]}
        assert {"online_mode", "cloud_test_switch"} <= failed
        response = self.client.post("/api/ai-tests/run", json={
            "post_id": self.post_id, "preview_fingerprint": preview["preview_fingerprint"],
            "idempotency_key": "offline-run", "confirmed_external_send": True,
            "accepted_data_handling": True, "accepted_unknown_cost": True,
        })
        assert response.status_code == 409 and type(self).mock.calls == []

    def test_one_redacted_request_idempotency_metrics_and_old_draft_unchanged(self):
        first = self._run()
        assert first.status_code == 201 and first.json()["status"] == "succeeded"
        second = self._run()
        assert second.status_code == 201 and second.json()["id"] == first.json()["id"]
        assert len(type(self).mock.calls) == 1
        outbound = json.dumps(type(self).mock.calls[0].messages, ensure_ascii=False)
        assert "٠٧٧٠" not in outbound and "private.owner" not in outbound
        assert "photo.jpg" not in outbound and "private.example/source" not in outbound
        assert "طابو" in outbound
        with self.Session() as session:
            listing = session.scalar(select(ListingDraft))
            assert listing.title == "المسودة القديمة" and listing.price == 100000
            assert session.scalar(select(func.count(AITestRun.id))) == 1
            metric = session.scalar(select(ProviderRuntimeMetric).order_by(ProviderRuntimeMetric.id.desc()))
            assert metric.request_count == 1 and metric.total_tokens == 80

    def test_missing_usage_and_cost_remain_unavailable(self):
        type(self).mock.response = replace(
            type(self).mock.response, input_tokens=None, output_tokens=None, total_tokens=None,
            actual_cost=None, cost_currency=None,
        )
        payload = self._run("missing-usage").json()
        assert payload["input_tokens"] is None and payload["output_tokens"] is None
        assert payload["actual_cost"] is None and payload["cost_status"] == "unavailable"

    def test_redacted_raw_response_has_bounded_retention_and_is_purged(self):
        payload = self._run("retention-run").json()
        assert payload["raw_response_expires_at"] is not None
        with self.Session.begin() as session:
            row = session.get(AITestRun, payload["id"])
            assert row.raw_response_redacted and len(row.raw_response_redacted) <= 32_768
            row.raw_response_expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert self.client.get(f"/api/ai-tests/{payload['id']}").status_code == 200
        with self.Session() as session:
            row = session.get(AITestRun, payload["id"])
            assert row.raw_response_redacted is None and row.raw_response_expires_at is None

    def test_reported_cost_above_cap_is_a_policy_failure(self):
        type(self).mock.response = replace(
            type(self).mock.response, actual_cost=0.001, cost_currency="USD",
        )
        payload = self._run("cost-cap-run").json()
        assert payload["status"] == "failed"
        assert payload["failure_type"] == "cost_cap_exceeded"
        assert payload["cost_status"] == "cap_exceeded"

    @pytest.mark.parametrize("status_code", [401, 429, 500])
    def test_http_failures_are_persisted_without_retry(self, status_code):
        type(self).mock.failure = ProviderFailure(
            "http_error", f"Kilo returned HTTP {status_code}", http_status=status_code,
            duration_ms=10, raw_body='{"error":"safe"}',
        )
        payload = self._run(f"http-{status_code}").json()
        assert payload["status"] == "failed" and payload["http_status"] == status_code
        assert len(type(self).mock.calls) == 1

    def test_timeout_is_persisted_without_retry(self):
        type(self).mock.failure = ProviderFailure("timeout", "Kilo request timed out", duration_ms=500)
        payload = self._run("timeout-run").json()
        assert payload["status"] == "failed" and payload["failure_type"] == "timeout"
        assert len(type(self).mock.calls) == 1

    @pytest.mark.parametrize("content,finish,expected", [
        ('{"category":"for_sale"', "length", "truncated_json"),
        ("not-json", "stop", "invalid_json"),
    ])
    def test_invalid_model_output_is_a_failed_attempt(self, content, finish, expected):
        type(self).mock.response = replace(type(self).mock.response, content=content, finish_reason=finish)
        payload = self._run("bad-output-" + expected).json()
        assert payload["status"] == "failed" and payload["failure_type"] == expected

    def test_database_constraint_blocks_a_second_active_test(self):
        preview = self._preview()
        with self.Session.begin() as session:
            provider = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == "kilo"))
            session.add(AITestRun(
                source_post_id=self.post_id, provider_config_id=provider.id, idempotency_key="already-active",
                preview_fingerprint=preview["preview_fingerprint"], status="running",
                requested_model="kilo-auto/free", prompt_snapshot={}, redacted_input="safe",
            ))
        response = self._run("second-active")
        assert response.status_code == 409
        assert type(self).mock.calls == []

    def test_provider_request_limit_blocks_a_second_send(self):
        with self.Session.begin() as session:
            provider = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == "kilo"))
            provider.request_limit = 1
        assert self._run("limit-first").json()["status"] == "succeeded"
        blocked = self._run("limit-second")
        assert blocked.status_code == 409 and len(type(self).mock.calls) == 1

    def test_review_is_local_and_term_suggestion_does_not_change_dictionary(self):
        run = self._run("review-run").json()
        accepted = self.client.post(f"/api/ai-tests/{run['id']}/review", json={"action": "accept_for_test"})
        suggested = self.client.post(f"/api/ai-tests/{run['id']}/review", json={
            "action": "suggest_term", "suggested_term": "واجهة", "note": "مصطلح محلي",
        })
        assert accepted.status_code == 201 and suggested.status_code == 201
        detail = self.client.get(f"/api/ai-tests/{run['id']}").json()
        assert detail["review_status"] == "accepted_for_test" and len(detail["reviews"]) == 2
        with self.Session() as session:
            assert session.scalar(select(func.count(DialectTerm.id)).where(DialectTerm.term == "واجهة")) == 0
            listing = session.scalar(select(ListingDraft))
            assert listing.review_status == "approved"

    def test_no_secret_field_in_schema_or_openapi(self):
        with self.engine.connect() as connection:
            schema = " ".join(row[0] or "" for row in connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='table'"
            ))
        assert "api_key" not in schema.lower()
        openapi = self.client.get("/openapi.json").json()
        assert "kilo_api_key" not in json.dumps(openapi).lower()
        assert {
            "/api/ai-tests/preview", "/api/ai-tests/run", "/api/ai-tests/{test_id}",
            "/api/ai-tests", "/api/ai-tests/{test_id}/review",
        } <= set(openapi["paths"])
