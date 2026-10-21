"""Phase 3A tests: ports, monitoring separation, providers, and migrations."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from contextlib import closing
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
from backend.config import ConfigError, Settings  # noqa: E402
from backend.database import Base, get_session  # noqa: E402
from backend.main import app  # noqa: E402
from backend.migrations import EXPECTED_REVISION, backup_database, upgrade_database  # noqa: E402
from backend.models import AIProviderConfig, ModelUsage, ProviderRuntimeMetric  # noqa: E402
from backend.ports import select_backend_port  # noqa: E402
from backend.seed import seed_provider_configs  # noqa: E402


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestPorts:
    def test_backend_port_defaults_and_environment_override(self):
        with patch.dict(os.environ, {}, clear=True):
            assert Settings.load().backend_port == 8000
        with patch.dict(os.environ, {"AQARATI_BACKEND_PORT": "8010"}, clear=True):
            assert Settings.load().backend_port == 8010
        with patch.dict(os.environ, {"AQARATI_BACKEND_PORT": "invalid"}, clear=True):
            try:
                Settings.load()
                assert False, "invalid port must fail"
            except ConfigError:
                pass

    def test_default_port_falls_back_without_stopping_a_process(self):
        with patch("backend.ports.is_port_available", side_effect=[False, True]):
            assert select_backend_port(8000) == (8010, True)

    def test_vite_proxy_uses_same_environment_port(self):
        script = (
            "import {backendTarget} from './port-config.mjs';"
            "console.log(JSON.stringify([backendTarget({}),"
            "backendTarget({AQARATI_BACKEND_PORT:'8010'})]))"
        )
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", script],
            cwd=PROJECT_ROOT / "frontend", capture_output=True, text=True, check=True,
        )
        assert json.loads(result.stdout) == ["http://127.0.0.1:8000", "http://127.0.0.1:8010"]


class TestProviderAndMonitoringAPI:
    @classmethod
    def setup_class(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
            seed_provider_configs(session)

    def test_provider_defaults_are_disabled_and_unconnected(self):
        response = self.client.get("/api/models/providers")
        assert response.status_code == 200
        providers = response.json()
        assert {row["provider_key"] for row in providers} == {"kilo", "ollama", "openvino"}
        assert all(row["is_enabled"] is False for row in providers)
        assert all(row["connection_status"] == "not_tested" for row in providers)
        assert "api_key" not in response.text.lower()
        with self.engine.connect() as connection:
            schema = " ".join(row[0] or "" for row in connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='table'"
            ))
        assert "api_key" not in schema.lower()
        assert "secret" not in schema.lower()
        assert "api_key" not in json.dumps(self.client.get("/openapi.json").json()).lower()

    def test_provider_validation_and_secret_rejection(self):
        provider_id = self.client.get("/api/models/providers").json()[0]["id"]
        secret = self.client.patch(
            f"/api/models/providers/{provider_id}", json={"api_key": "must-not-be-stored"}
        )
        assert secret.status_code == 422
        unsafe = self.client.patch(
            f"/api/models/providers/{provider_id}",
            json={"operation_mode": "local", "api_base_url": "https://remote.example"},
        )
        assert unsafe.status_code == 422
        missing_model = self.client.patch(
            f"/api/models/providers/{provider_id}", json={"is_enabled": True}
        )
        assert missing_model.status_code == 422

    def test_historical_and_live_metrics_are_not_mixed(self):
        with self.Session.begin() as session:
            provider = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == "ollama"))
            session.add(ModelUsage(provider="legacy", request_count=226, input_tokens=10,
                                   output_tokens=None, total_tokens=10, metric_scope="historical"))
            session.add(ProviderRuntimeMetric(provider_config_id=provider.id, request_count=3,
                        input_tokens=None, output_tokens=None, total_tokens=None,
                        average_response_time_ms=None, connection_errors=1))
        dashboard = self.client.get("/api/dashboard").json()
        assert dashboard["historical_import"]["actual_api_requests"] == 226
        assert dashboard["live_monitoring"]["request_count"] == 3
        assert dashboard["live_monitoring"]["input_tokens"] is None
        live = self.client.get("/api/models/live").json()
        ollama = next(row for row in live if row["provider"]["provider_key"] == "ollama")
        assert ollama["metrics"]["request_count"] == 3
        assert ollama["metrics"]["total_tokens"] is None

    def test_no_live_rows_returns_unavailable_not_zero(self):
        dashboard = self.client.get("/api/dashboard").json()["live_monitoring"]
        assert dashboard["request_count"] is None
        assert dashboard["input_tokens"] is None
        assert dashboard["output_tokens"] is None


class TestMigrations:
    def test_upgrade_chain_and_backup_on_disposable_database(self):
        relative = Path("data/processed/_phase3a_migration_test.sqlite3")
        database = PROJECT_ROOT / relative
        for candidate in database.parent.glob("_phase3a_migration_test*.sqlite3"):
            candidate.unlink()
        previous = os.environ.get("AQARATI_LAB_DATABASE")
        os.environ["AQARATI_LAB_DATABASE"] = relative.as_posix()
        try:
            configuration = Config(str(PROJECT_ROOT / "alembic.ini"))
            command.upgrade(configuration, "20261021_01")
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20261021_01"
            backup, revision = upgrade_database(database, create_backup=True)
            assert revision == EXPECTED_REVISION
            assert backup and backup.exists()
            with closing(sqlite3.connect(backup)) as connection:
                assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20261021_01"
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == EXPECTED_REVISION
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                assert {"ai_provider_configs", "provider_runtime_metrics"} <= tables
                assert connection.execute("SELECT COUNT(*) FROM ai_provider_configs").fetchone()[0] == 3
        finally:
            if previous is None:
                os.environ.pop("AQARATI_LAB_DATABASE", None)
            else:
                os.environ["AQARATI_LAB_DATABASE"] = previous
            for candidate in database.parent.glob("_phase3a_migration_test*.sqlite3"):
                candidate.unlink()
            backup_dir = database.parent / "backups"
            if backup_dir.exists():
                for candidate in backup_dir.glob("_phase3a_migration_test*.sqlite3"):
                    candidate.unlink()

    def test_legacy_project_files_remain_read_only(self):
        legacy = paths.repo_path("real_estate_ai_pipeline", "output", "aqarati_50_results.json")
        if not legacy.exists():
            return
        before = _digest(legacy)
        with patch("backend.ports.is_port_available", return_value=True):
            select_backend_port(8000)
        assert _digest(legacy) == before
