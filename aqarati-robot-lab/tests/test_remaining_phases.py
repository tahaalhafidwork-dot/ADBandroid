"""End-to-end local/Mock acceptance tests for phases 3C, 4, and 5."""

from __future__ import annotations

import base64
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from . import PROJECT_ROOT as PROJECT_ROOT_STRING

PROJECT_ROOT = Path(PROJECT_ROOT_STRING)

from backend import paths  # noqa: E402
from backend.ai_tests import get_ai_provider_factory  # noqa: E402
from backend.database import Base, get_session  # noqa: E402
from backend.integration_api import get_aqarati_connector_factory  # noqa: E402
from backend.integrations.aqarati import SyncResponse  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import (  # noqa: E402
    AIProviderConfig, AqaratiSyncRecord, ListingDraft, OCRResult,
    ProcessingJob, ProcessingJobItem, SourcePost,
)
from backend.ocr import OCRFailure, download_image, extract_suggestions  # noqa: E402
from backend.ocr_api import get_ocr_engine  # noqa: E402
from backend.processing.jobs import process_job_step, recover_interrupted_jobs  # noqa: E402
from backend.providers.base import ProviderFailure, ProviderRequest, ProviderResponse  # noqa: E402
from backend.seed import seed_reference_data  # noqa: E402


def extracted_payload():
    return {
        "category": "for_sale", "property_type": "house", "title": "بيت للبيع",
        "description": None, "price": 250000000, "price_text": "250 مليون دينار",
        "currency": "IQD", "area_sqm": 200, "area_text": "200 متر", "area_donum": None,
        "negotiable": True, "installment_available": False, "down_payment": None,
        "payment_terms": None, "bedrooms": 3, "bathrooms": 2, "city": "بغداد",
        "district": "المنصور", "complex_name": None, "floor": None, "furnished": None,
        "confidence": 0.94, "uncertain_fields": [], "needs_review": False, "review_notes": [],
    }


class MockProvider:
    def __init__(self):
        self.calls: list[ProviderRequest] = []
        self.failure: ProviderFailure | None = None

    def complete(self, request: ProviderRequest):
        self.calls.append(request)
        if self.failure:
            raise self.failure
        return ProviderResponse(
            content=json.dumps(extracted_payload(), ensure_ascii=False), requested_model=request.model,
            actual_model="local/mock", http_status=200, finish_reason="stop", duration_ms=12,
            input_tokens=40, output_tokens=40, total_tokens=80, actual_cost=0, cost_currency="USD",
            raw_body='{"safe":true}',
        )


class MockOCR:
    name = "mock-local-ocr"

    def extract(self, _image: bytes, _languages: str):
        return "السعر 125000 IQD المساحة 140 م الطابق 3"


class MockAqarati:
    def __init__(self): self.calls: list[tuple[dict, str]] = []
    def capabilities(self): return {"can_create_drafts": True, "can_publish": False}
    def create_draft(self, payload: dict, key: str):
        self.calls.append((payload, key)); return SyncResponse("mock-draft-1", 201)


class TestRemainingPhases:
    @classmethod
    def setup_class(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        cls.provider = MockProvider(); cls.aqarati = MockAqarati()

        def override_session():
            with cls.Session() as session: yield session

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_ai_provider_factory] = lambda: (lambda _config, _secret: cls.provider)
        app.dependency_overrides[get_ocr_engine] = lambda: MockOCR()
        app.dependency_overrides[get_aqarati_connector_factory] = lambda: (lambda _config, _token: cls.aqarati)
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        app.dependency_overrides.clear(); Base.metadata.drop_all(cls.engine); cls.engine.dispose()

    def setup_method(self):
        self.provider.calls.clear(); self.provider.failure = None; self.aqarati.calls.clear()
        with self.Session.begin() as session:
            for table in reversed(Base.metadata.sorted_tables): session.execute(table.delete())
            seed_reference_data(session)
            local = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == "ollama"))
            local.is_enabled = True; local.model_name = "local/mock"; local.api_base_url = "http://127.0.0.1:11434"
            for index in range(1, 4):
                session.add(SourcePost(source_identifier=f"post-{index}", source_fingerprint=f"{'a' * 63}{index}",
                    source="synthetic", original_text=f"بيت للبيع في بغداد {index}", image_urls=[]))

    def _create_job(self, ids=(1,), **changes):
        payload = {"name":"mock batch", "post_ids":list(ids), "provider_key":"ollama", "max_retries":1,
                   "max_requests":10, "max_tokens_budget":1000, "max_cost_budget":0,
                   "force_reprocess":False, "confirmed_cloud_processing":False}
        payload.update(changes)
        response = self.client.post("/api/processing/jobs", json=payload)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def test_single_and_batch_processing_persist_each_result_and_block_duplicates(self):
        job_id = self._create_job((1, 2))
        with self.Session() as session:
            assert process_job_step(session, job_id, lambda _config, _secret: self.provider) == "succeeded"
            first = session.scalar(select(ProcessingJobItem).where(ProcessingJobItem.job_id == job_id).order_by(ProcessingJobItem.position))
            assert first.status == "succeeded" and first.ai_test_run_id is not None
            assert process_job_step(session, job_id, lambda _config, _secret: self.provider) == "succeeded"
            job = session.get(ProcessingJob, job_id)
            assert job.status == "completed" and job.completed_posts == 2 and job.actual_requests == 2
            assert job.total_tokens == 160 and job.actual_cost == 0
        assert len(self.provider.calls) == 2
        duplicate = self.client.post("/api/processing/jobs", json={"name":"again","post_ids":[1],"provider_key":"ollama",
            "max_retries":0,"max_requests":1,"max_tokens_budget":100,"max_cost_budget":0,
            "force_reprocess":False,"confirmed_cloud_processing":False})
        assert duplicate.status_code == 409

    def test_pause_recovery_api_error_and_budget_limits(self):
        paused_id = self._create_job((1,))
        assert self.client.post(f"/api/processing/jobs/{paused_id}/pause").json()["status"] == "paused"
        with self.Session.begin() as session:
            job = session.get(ProcessingJob, paused_id); job.status = "running"
            job.items[0].status = "running"
        with self.Session() as session:
            assert recover_interrupted_jobs(session) == 1
            assert session.get(ProcessingJob, paused_id).status == "queued"
            assert session.get(ProcessingJob, paused_id).items[0].status == "queued"

        limited_id = self._create_job((2, 3), max_tokens_budget=79)
        with self.Session() as session:
            assert process_job_step(session, limited_id, lambda _c, _s: self.provider) == "succeeded"
            assert process_job_step(session, limited_id, lambda _c, _s: self.provider) == "limit_reached"
            assert session.get(ProcessingJob, limited_id).status == "limit_reached"

        error_id = self._create_job((1,), force_reprocess=True)
        self.provider.failure = ProviderFailure("rate_limited", "HTTP 429", http_status=429)
        with self.Session() as session:
            assert process_job_step(session, error_id, lambda _c, _s: self.provider) == "failed"
            item = session.scalar(select(ProcessingJobItem).where(ProcessingJobItem.job_id == error_id))
            assert item.last_error_type == "rate_limited"

    def test_historical_job_counters_are_not_rewritten_by_live_queue(self):
        with self.Session.begin() as session:
            historical = ProcessingJob(name="historical import", status="completed", total_posts=5,
                completed_posts=4, failed_posts=1, provider_config_id=None)
            session.add(historical); session.flush(); historical_id = historical.id
        rows = self.client.get("/api/processing/jobs").json()
        row = next(item for item in rows if item["id"] == historical_id)
        assert (row["total_posts"], row["completed_posts"], row["failed_posts"]) == (5, 4, 1)
        with self.Session() as session:
            saved = session.get(ProcessingJob, historical_id)
            assert (saved.completed_posts, saved.failed_posts) == (4, 1)

    def test_ocr_local_image_suggestions_correction_and_safe_network_block(self):
        image = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        source = paths.data_path("raw", "_ocr_synthetic.png")
        paths.write_bytes(source, image)
        try:
            response = self.client.post("/api/ocr/extract", json={"post_id":1,"image_index":None,
                "local_path":"raw/_ocr_synthetic.png","languages":"ara+kur+eng"})
            assert response.status_code == 201, response.text
            result = response.json(); assert result["status"] == "succeeded" and result["image_url"]
            assert result["suggestions"]["price"] == 125000
            assert self.client.get(result["image_url"]).status_code == 200
            corrected = self.client.patch(f"/api/ocr/{result['id']}", json={"corrected_text":"المساحة 200 م"})
            assert corrected.json()["suggestions"]["area_sqm"] == 200
            review = self.client.post(f"/api/ocr/{result['id']}/review", json={"action":"approve"}).json()
            assert review["listing_modified"] is False
            with patch("backend.ocr.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 0))]):
                try: download_image("http://localhost/private.png"); assert False
                except OCRFailure as exc: assert exc.kind == "private_network_blocked"
        finally:
            source.unlink(missing_ok=True)
            with self.Session() as session:
                for row in session.scalars(select(OCRResult)).all():
                    if row.cached_image_path: paths.data_path(*row.cached_image_path.split("/")).unlink(missing_ok=True)

    def test_local_model_discovery_uses_loopback_and_never_starts_or_downloads(self):
        with patch("backend.local_models.discover_local_models", return_value=["llama-local"]):
            response = self.client.get("/api/local-models/ollama/discover")
        assert response.status_code == 200
        assert response.json() == {"provider_key":"ollama","models":["llama-local"],"installed":True,"started_by_lab":False}
        unsafe = self.client.patch("/api/models/providers/2", json={"api_base_url":"https://remote.example"})
        assert unsafe.status_code == 422

    def test_mock_aqarati_full_draft_flow_is_idempotent_and_never_publishes(self):
        with self.Session.begin() as session:
            post = session.get(SourcePost, 1); post.image_urls = ["https://images.example/synthetic.png"]
            session.add(ListingDraft(source_post_id=1, listing_type="for_sale", property_type="house",
                title="بيت مختبري", price=250000000, currency="IQD", city="بغداد",
                verification_status="verified", review_status="approved"))
        with patch.dict(os.environ, {"AQARATI_LAB_ENABLE_AQARATI_SYNC":"true", "AQARATI_SERVICE_TOKEN":"runtime-only"}, clear=False):
            config = self.client.patch("/api/aqarati/config", json={"base_url":"https://aqarati.example",
                "service_identity":"Aqarati Robot","draft_path":"/api/robot/drafts","is_enabled":True})
            assert config.status_code == 200 and "runtime-only" not in config.text
            listing_id = self.client.get("/api/listings?review_status=approved").json()["items"][0]["id"]
            data = {"listing_id":listing_id,"idempotency_key":"mock-draft-key","confirmed_draft_sync":True,
                    "include_images":True,"confirmed_image_rights":True}
            first = self.client.post("/api/aqarati/sync", json=data)
            second = self.client.post("/api/aqarati/sync", json=data)
        assert first.status_code == 201 and first.json()["status"] == "draft_created"
        assert second.json()["id"] == first.json()["id"] and len(self.aqarati.calls) == 1
        sent, key = self.aqarati.calls[0]
        assert key == "mock-draft-key" and sent["lifecycle"] == "draft" and sent["publish"] is False
        assert sent["images"] == ["https://images.example/synthetic.png"]
        with self.Session() as session: assert session.scalar(select(AqaratiSyncRecord)).remote_draft_id == "mock-draft-1"

    def test_complete_mock_workflow_from_post_to_reviewed_aqarati_draft(self):
        job_id = self._create_job((1,))
        with self.Session() as session:
            assert process_job_step(session, job_id, lambda _c, _s: self.provider) == "succeeded"
            item = session.scalar(select(ProcessingJobItem).where(ProcessingJobItem.job_id == job_id))
            assert item.ai_test_run_id is not None
            result = extracted_payload()
            listing = ListingDraft(source_post_id=1, listing_type=result["category"], property_type=result["property_type"],
                title=result["title"], price=result["price"], currency=result["currency"], area_sqm=result["area_sqm"],
                city=result["city"], district=result["district"], confidence=result["confidence"],
                verification_status="verified", review_status="approved", provider="mock", model_name="local/mock")
            session.add(listing); session.commit(); listing_id = listing.id
        with patch.dict(os.environ, {"AQARATI_LAB_ENABLE_AQARATI_SYNC":"true", "AQARATI_SERVICE_TOKEN":"runtime-only"}, clear=False):
            self.client.patch("/api/aqarati/config", json={"base_url":"https://aqarati.example",
                "service_identity":"Aqarati Robot","draft_path":"/api/robot/drafts","is_enabled":True})
            response = self.client.post("/api/aqarati/sync", json={"listing_id":listing_id,
                "idempotency_key":"complete-mock-flow","confirmed_draft_sync":True,
                "include_images":False,"confirmed_image_rights":False})
        assert response.status_code == 201 and response.json()["remote_draft_id"] == "mock-draft-1"
        assert self.aqarati.calls[-1][0]["publish"] is False

    def test_iraqi_extraction_preserves_original_price_and_missing_values(self):
        parsed = extracted_payload(); parsed["price"] = None; parsed["price_text"] = "السعر عالخاص"
        assert parsed["price"] is None and parsed["price_text"] == "السعر عالخاص"
        suggestions = extract_suggestions("السعر 75,000,000 دينار والمساحة 300 م")
        assert suggestions["currency"] == "IQD" and suggestions["area_sqm"] == 300


def test_migration_from_phase3b_preserves_existing_data():
    relative = Path("data/processed/_remaining_phases_migration.sqlite3")
    database = PROJECT_ROOT / relative
    database.unlink(missing_ok=True)
    previous = os.environ.get("AQARATI_LAB_DATABASE")
    os.environ["AQARATI_LAB_DATABASE"] = relative.as_posix()
    try:
        configuration = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(configuration, "20261021_03")
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("INSERT INTO dialect_terms (term,meaning,approval_status,created_at,updated_at) VALUES (?,?,?,?,?)",
                ("اختبار", "يبقى", "approved", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
            connection.commit()
        command.upgrade(configuration, "head")
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT meaning FROM dialect_terms WHERE term='اختبار'").fetchone()[0] == "يبقى"
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20261021_04"
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert {"processing_job_items","ocr_results","aqarati_sync_records"} <= tables
    finally:
        if previous is None: os.environ.pop("AQARATI_LAB_DATABASE", None)
        else: os.environ["AQARATI_LAB_DATABASE"] = previous
        database.unlink(missing_ok=True)
