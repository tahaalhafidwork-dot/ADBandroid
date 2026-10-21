"""Back up the selected local database and apply all Alembic migrations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import paths  # noqa: E402
from backend.config import Settings  # noqa: E402
from backend.migrations import copy_database, upgrade_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", help="project-relative SQLite path; defaults to configured database")
    parser.add_argument("--no-backup", action="store_true", help="only for a disposable test database")
    parser.add_argument("--test-copy", help="copy the configured database to this project-relative path and migrate only the copy")
    arguments = parser.parse_args()
    if arguments.database and arguments.test_copy:
        parser.error("--database and --test-copy cannot be combined")
    source = Settings.load().database_path
    if arguments.test_copy:
        database = paths.project_path(arguments.test_copy)
        copy_database(source, database)
        backup, revision = upgrade_database(database, create_backup=False)
        print("Source preserved: {0}".format(source.relative_to(paths.PROJECT_ROOT).as_posix()))
        print("Test copy: {0}".format(database.relative_to(paths.PROJECT_ROOT).as_posix()))
    else:
        database = paths.project_path(arguments.database) if arguments.database else source
        backup, revision = upgrade_database(database, create_backup=not arguments.no_backup)
    print("Migration complete: {0}".format(revision))
    print("Database: {0}".format(database.relative_to(paths.PROJECT_ROOT).as_posix()))
    print("Backup: {0}".format(backup.relative_to(paths.PROJECT_ROOT).as_posix() if backup else "not required"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
