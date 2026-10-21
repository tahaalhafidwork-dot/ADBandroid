"""Create the phase-two local monitoring schema."""

from alembic import op

from backend.database import Base
from backend import models  # noqa: F401

revision = "20261021_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

