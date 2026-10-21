"""Backup-first Alembic migration helpers."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from . import paths

EXPECTED_REVISION = "20261021_02"


def backup_database(database_path: Path) -> Path | None:
    """Create a consistent SQLite backup inside data/processed/backups/."""
    source = paths.ensure_inside_project(database_path)
    if not source.exists() or source.stat().st_size == 0:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = paths.safe_write_path(
        paths.data_path("processed", "backups", "{0}_{1}.sqlite3".format(source.stem, timestamp))
    )
    copy_database(source, backup)
    return backup


def copy_database(source_path: Path, destination_path: Path) -> Path:
    """Create a consistent disposable copy without modifying the source database."""
    source = paths.ensure_inside_project(source_path)
    destination = paths.safe_write_path(destination_path)
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination databases must differ")
    if not source.exists():
        raise FileNotFoundError("source database does not exist")
    if destination.exists():
        raise FileExistsError("refusing to overwrite an existing database copy")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)
    return destination


def upgrade_database(database_path: Path, *, create_backup: bool = True) -> tuple[Path | None, str]:
    target = paths.ensure_inside_project(database_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = backup_database(target) if create_backup else None
    previous = os.environ.get("AQARATI_LAB_DATABASE")
    os.environ["AQARATI_LAB_DATABASE"] = target.relative_to(paths.PROJECT_ROOT).as_posix()
    try:
        configuration = Config(str(paths.project_path("alembic.ini")))
        command.upgrade(configuration, "head")
    finally:
        if previous is None:
            os.environ.pop("AQARATI_LAB_DATABASE", None)
        else:
            os.environ["AQARATI_LAB_DATABASE"] = previous

    from .models import AIProviderConfig, DialectTerm
    from .seed import seed_reference_data

    migration_engine = create_engine("sqlite:///{0}".format(target.as_posix()))
    with Session(migration_engine) as session:
        seed_reference_data(session)
        session.commit()
    migration_engine.dispose()
    return backup, EXPECTED_REVISION
