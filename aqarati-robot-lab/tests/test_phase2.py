"""Synthetic tests for the phase-two database, API, and import adapter."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from . import PROJECT_ROOT  # noqa: F401

from backend.database import Base, get_session  # noqa: E402
from backend.import_service import _add_post, _records  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import ListingDraft, ModelUsage, ReviewAction, SourcePost  # noqa: E402


class TestPhaseTwo:
    @classmethod
    def setup_class(cls):
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)

        def override_session():
            with cls.Session() as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        cls.client = TestClient(app)

    @classmethod
    def teardown_class(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setup_method(self):
        with self.Session.begin() as session:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())

    def _seed_posts(self):
        with self.Session.begin() as session:
            added, first = _add_post(session, 1, {
                "source_url": "synthetic://sale/1", "text": "بيانات اختبار اصطناعية",
                "listing_type": "for_sale", "city": "بغداد", "price": 100,
                "_status": "ok", "_provider": "synthetic",
            }, "accepted", 0)
            assert added and first
            duplicate, _ = _add_post(session, 1, {
                "source_url": "synthetic://sale/1", "text": "بيانات اختبار اصطناعية",
                "listing_type": "for_sale", "_status": "ok",
            }, "accepted", 1)
            assert not duplicate
            _add_post(session, 1, {
                "url": "synthetic://bad/1", "text": "بيانات اختبار اصطناعية مرفوضة",
                "category": "unclear", "status": "truncated",
                "reason": "Extraction failed while parsing truncated JSON",
            }, "rejected", 0)

    def test_supported_legacy_shapes_are_validated(self):
        accepted, rejected, duplicates, stats = _records({
            "structured_listings": [{"id": 1}], "rejected_posts": [{"id": 2}],
            "duplicates": [{"id": 3}], "stats": {"total_posts": 3},
        })
        assert [len(accepted), len(rejected), len(duplicates)] == [1, 1, 1]
        assert stats["total_posts"] == 3
        accepted, rejected, duplicates, _ = _records([{"id": 1}])
        assert len(accepted) == 1 and not rejected and not duplicates

    def test_deduplication_and_unique_drafts(self):
        self._seed_posts()
        with self.Session() as session:
            assert session.scalar(select(func.count(SourcePost.id))) == 2
            assert session.scalar(select(func.count(ListingDraft.id))) == 1
            rejected = session.scalar(select(SourcePost).where(SourcePost.processing_status == "rejected"))
            assert rejected.has_json_error is True
            assert rejected.is_truncated is True

    def test_dashboard_is_calculated_from_database(self):
        self._seed_posts()
        response = self.client.get("/api/dashboard")
        assert response.status_code == 200
        metrics = response.json()["historical_import"]
        assert metrics["imported_posts"] == 2
        assert metrics["unique_imported_posts"] == 2
        assert metrics["json_errors"] == 1
        assert metrics["truncated_responses"] == 1

    def test_listing_patch_creates_audit_action(self):
        self._seed_posts()
        with self.Session() as session:
            listing_id = session.scalar(select(ListingDraft.id))
        response = self.client.patch(
            "/api/listings/{0}".format(listing_id),
            json={"price": 125, "review_status": "approved"},
        )
        assert response.status_code == 200
        assert response.json()["price"] == 125
        with self.Session() as session:
            action = session.scalar(select(ReviewAction))
            assert action.changes["price"] == {"before": 100.0, "after": 125.0}

    def test_model_usage_preserves_unknown_values(self):
        with self.Session.begin() as session:
            session.add(ModelUsage(provider="synthetic", model_name=None, request_count=2,
                                   input_tokens=10, output_tokens=None, total_tokens=10))
        payload = self.client.get("/api/models/usage").json()[0]
        assert payload["output_tokens"] is None
        assert payload["actual_cost"] is None

    def test_origin_guard_and_input_validation(self):
        blocked = self.client.post(
            "/api/dialect/terms", headers={"Origin": "https://invalid.example"},
            json={"term": "س", "meaning": "اختبار"},
        )
        assert blocked.status_code == 403
        invalid = self.client.patch("/api/listings/999", json={"unknown": "value"})
        assert invalid.status_code == 422

    def test_openapi_exposes_all_required_routes(self):
        route_paths = self.client.get("/openapi.json").json()["paths"]
        required = {
            "/api/health", "/api/dashboard", "/api/posts", "/api/posts/{post_id}",
            "/api/listings", "/api/listings/{listing_id}", "/api/jobs",
            "/api/models/usage", "/api/dialect/terms", "/api/dialect/terms/{term_id}",
            "/api/imports/legacy",
        }
        assert required <= set(route_paths)
