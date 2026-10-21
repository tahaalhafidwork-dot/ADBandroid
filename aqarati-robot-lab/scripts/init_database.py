"""Apply migrations and install the editable Iraqi dialect seed terms."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Settings  # noqa: E402
from backend.migrations import upgrade_database  # noqa: E402


if __name__ == "__main__":
    backup, revision = upgrade_database(Settings.load().database_path, create_backup=True)
    print("Database initialized at revision {0}.".format(revision))
    if backup:
        print("Backup: {0}".format(backup.relative_to(PROJECT_ROOT).as_posix()))
