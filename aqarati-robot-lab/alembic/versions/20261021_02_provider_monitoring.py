"""Add provider settings and isolated live monitoring.

Revision ID: 20261021_02
Revises: 20261021_01
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021_02"
down_revision = "20261021_01"
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "ai_provider_configs" not in tables:
        op.create_table(
            "ai_provider_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_key", sa.String(50), nullable=False, unique=True),
            sa.Column("display_name", sa.String(100), nullable=False),
            sa.Column("api_base_url", sa.String(500), nullable=False),
            sa.Column("model_name", sa.String(200)),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("operation_mode", sa.String(20), nullable=False),
            sa.Column("max_tokens", sa.Integer()),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("request_limit", sa.Integer()),
            sa.Column("cost_cap", sa.Float()),
            sa.Column("connection_status", sa.String(30), nullable=False, server_default="not_tested"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "provider_runtime_metrics" not in tables:
        op.create_table(
            "provider_runtime_metrics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_config_id", sa.Integer(), sa.ForeignKey("ai_provider_configs.id"), nullable=False),
            sa.Column("request_count", sa.Integer()),
            sa.Column("input_tokens", sa.Integer()),
            sa.Column("output_tokens", sa.Integer()),
            sa.Column("total_tokens", sa.Integer()),
            sa.Column("average_response_time_ms", sa.Float()),
            sa.Column("connection_errors", sa.Integer()),
            sa.Column("last_activity_at", sa.DateTime(timezone=True)),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_provider_runtime_metrics_provider_config_id", "provider_runtime_metrics", ["provider_config_id"])

    inspector = sa.inspect(bind)
    if "source_posts" in inspector.get_table_names():
        columns = _columns(inspector, "source_posts")
        if "duplicate_classification" not in columns:
            op.add_column("source_posts", sa.Column("duplicate_classification", sa.String(30)))
            op.create_index("ix_source_posts_duplicate_classification", "source_posts", ["duplicate_classification"])
        bind.execute(sa.text("UPDATE source_posts SET duplicate_classification='confirmed' WHERE is_duplicate=1 AND duplicate_classification IS NULL"))

    inspector = sa.inspect(bind)
    if "model_usage" in inspector.get_table_names():
        columns = _columns(inspector, "model_usage")
        if "metric_scope" not in columns:
            op.add_column("model_usage", sa.Column("metric_scope", sa.String(20), nullable=False, server_default="historical"))
            op.create_index("ix_model_usage_metric_scope", "model_usage", ["metric_scope"])
        if "source_label" not in columns:
            op.add_column("model_usage", sa.Column("source_label", sa.String(100)))
        bind.execute(sa.text("UPDATE model_usage SET metric_scope='historical' WHERE metric_scope IS NULL OR metric_scope=''"))


def downgrade() -> None:
    # Downgrade is intentionally non-destructive: phase 3A never drops provider
    # settings, monitoring tables, or imported data.
    pass

