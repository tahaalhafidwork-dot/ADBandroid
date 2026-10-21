"""Apply migrations and install the editable Iraqi dialect seed terms."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal  # noqa: E402
from backend.seed import seed_dialect_terms  # noqa: E402


if __name__ == "__main__":
    configuration = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(configuration, "head")
    with SessionLocal.begin() as session:
        seed_dialect_terms(session)
    print("Database initialized in data/processed/.")

