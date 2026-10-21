"""Configuration for Aqarati Robot AI Lab.

All locations are derived from the project root. Environment variables may
override a value, but only with a path that stays inside the project, so a
configuration file can never point the lab at a developer machine or at the
legacy projects.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import paths

ENV_PREFIX = "AQARATI_LAB_"


class ConfigError(ValueError):
    """Raised when an environment override is invalid."""


def _env_port(name: str, default: int) -> int:
    variable = "AQARATI_BACKEND_PORT" if name == "BACKEND_PORT" else ENV_PREFIX + name
    raw = os.environ.get(variable)
    if raw is None:
        return default
    try:
        port = int(raw)
    except ValueError as exc:
        raise ConfigError("{0} must be an integer".format(variable)) from exc
    if not 1 <= port <= 65535:
        raise ConfigError("{0} must be between 1 and 65535".format(variable))
    return port


def _env_path(name: str, default: Path) -> Path:
    """Read a path override from the environment, relative to the project."""
    raw = os.environ.get(ENV_PREFIX + name)
    if not raw:
        return default
    candidate = Path(raw)
    if candidate.is_absolute():
        raise ConfigError(
            "{0}{1} must be relative to the project root, got: {2}".format(
                ENV_PREFIX, name, raw
            )
        )
    resolved = paths.project_path(candidate)
    if not paths.is_inside(resolved, paths.PROJECT_ROOT):
        raise ConfigError(
            "{0}{1} escapes the project root: {2}".format(ENV_PREFIX, name, raw)
        )
    return resolved


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(ENV_PREFIX + name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable settings object for the lab."""

    project_root: Path
    data_root: Path
    raw_dir: Path
    processed_dir: Path
    legacy_dir: Path
    imports_dir: Path
    database_path: Path
    allow_pii_import: bool
    offline: bool
    enable_cloud_ai_test: bool
    enable_image_download: bool
    enable_aqarati_sync: bool
    backend_port: int

    @classmethod
    def load(cls) -> "Settings":
        """Build the settings from the project root and the environment."""
        data_root = _env_path("DATA_DIR", paths.data_path())
        return cls(
            project_root=paths.PROJECT_ROOT,
            data_root=data_root,
            raw_dir=_env_path("RAW_DIR", data_root / "raw"),
            processed_dir=_env_path("PROCESSED_DIR", data_root / "processed"),
            legacy_dir=_env_path("LEGACY_DIR", data_root / "legacy"),
            imports_dir=_env_path("IMPORTS_DIR", data_root / "imports"),
            database_path=_env_path("DATABASE", data_root / "processed" / "aqarati_lab.sqlite3"),
            allow_pii_import=_env_flag("ALLOW_PII_IMPORT", False),
            # The lab never talks to a paid service during scaffolding.
            offline=_env_flag("OFFLINE", True),
            # Separate kill switch: an operator must opt in immediately before
            # the single-post cloud experiment. It defaults to disabled.
            enable_cloud_ai_test=_env_flag("ENABLE_CLOUD_AI_TEST", False),
            enable_image_download=_env_flag("ENABLE_IMAGE_DOWNLOAD", False),
            enable_aqarati_sync=_env_flag("ENABLE_AQARATI_SYNC", False),
            backend_port=_env_port("BACKEND_PORT", 8000),
        )

    @property
    def manifest_path(self) -> Path:
        """Path of the import manifest (metadata only, safe to commit)."""
        return self.imports_dir / "manifest.json"

    def as_dict(self) -> dict:
        """Return a JSON friendly view with project relative paths."""
        return {
            "project_root": paths.relative_to_repo(self.project_root),
            "data_root": paths.relative_to_repo(self.data_root),
            "raw_dir": paths.relative_to_repo(self.raw_dir),
            "processed_dir": paths.relative_to_repo(self.processed_dir),
            "legacy_dir": paths.relative_to_repo(self.legacy_dir),
            "imports_dir": paths.relative_to_repo(self.imports_dir),
            "database_path": paths.relative_to_repo(self.database_path),
            "allow_pii_import": self.allow_pii_import,
            "offline": self.offline,
            "enable_cloud_ai_test": self.enable_cloud_ai_test,
            "enable_image_download": self.enable_image_download,
            "enable_aqarati_sync": self.enable_aqarati_sync,
            "backend_port": self.backend_port,
        }
