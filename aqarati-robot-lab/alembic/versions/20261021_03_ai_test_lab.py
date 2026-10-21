"""Add isolated single-post AI experiment records.

Revision ID: 20261021_03
Revises: 20261021_02
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021_03"
down_revision = "20261021_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "ai_test_runs" not in tables:
        op.create_table(
            "ai_test_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_post_id", sa.Integer(), sa.ForeignKey("source_posts.id"), nullable=False),
            sa.Column("provider_config_id", sa.Integer(), sa.ForeignKey("ai_provider_configs.id"), nullable=False),
            sa.Column("idempotency_key", sa.String(64), nullable=False),
            sa.Column("preview_fingerprint", sa.String(64), nullable=False),
            sa.Column("active_slot", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("requested_model", sa.String(200), nullable=False),
            sa.Column("actual_model", sa.String(200)),
            sa.Column("confirmed_external_send", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("accepted_data_handling", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("accepted_unknown_cost", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("duration_ms", sa.Float()),
            sa.Column("http_status", sa.Integer()),
            sa.Column("finish_reason", sa.String(100)),
            sa.Column("json_status", sa.String(30), nullable=False, server_default="not_checked"),
            sa.Column("schema_status", sa.String(30), nullable=False, server_default="not_checked"),
            sa.Column("failure_type", sa.String(100)),
            sa.Column("failure_message", sa.Text()),
            sa.Column("input_tokens", sa.Integer()),
            sa.Column("output_tokens", sa.Integer()),
            sa.Column("total_tokens", sa.Integer()),
            sa.Column("actual_cost", sa.Float()),
            sa.Column("cost_currency", sa.String(10)),
            sa.Column("cost_status", sa.String(30), nullable=False, server_default="unavailable"),
            sa.Column("extracted_result", sa.JSON()),
            sa.Column("prompt_snapshot", sa.JSON(), nullable=False),
            sa.Column("redacted_input", sa.Text(), nullable=False),
            sa.Column("raw_response_redacted", sa.Text()),
            sa.Column("raw_response_expires_at", sa.DateTime(timezone=True)),
            sa.Column("review_status", sa.String(30), nullable=False, server_default="unreviewed"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ai_test_runs_source_post_id", "ai_test_runs", ["source_post_id"])
        op.create_index("ix_ai_test_runs_provider_config_id", "ai_test_runs", ["provider_config_id"])
        op.create_index("ix_ai_test_runs_idempotency_key", "ai_test_runs", ["idempotency_key"], unique=True)
        op.create_index("ix_ai_test_runs_status", "ai_test_runs", ["status"])
        op.create_index(
            "uq_ai_test_one_active", "ai_test_runs", ["active_slot"], unique=True,
            sqlite_where=sa.text("status IN ('pending', 'running')"),
        )

    inspector = sa.inspect(bind)
    if "ai_test_reviews" not in inspector.get_table_names():
        op.create_table(
            "ai_test_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ai_test_run_id", sa.Integer(), sa.ForeignKey("ai_test_runs.id"), nullable=False),
            sa.Column("action", sa.String(40), nullable=False),
            sa.Column("note", sa.Text()),
            sa.Column("suggested_term", sa.String(120)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ai_test_reviews_ai_test_run_id", "ai_test_reviews", ["ai_test_run_id"])

    # Keep the provider disabled. Only align safe defaults with current official docs.
    if "ai_provider_configs" in inspector.get_table_names():
        bind.execute(sa.text(
            "UPDATE ai_provider_configs SET api_base_url=:url, "
            "model_name=COALESCE(NULLIF(model_name, ''), :model), "
            "max_tokens=COALESCE(max_tokens, 1800), cost_cap=COALESCE(cost_cap, 0) WHERE provider_key='kilo'"
        ), {"url": "https://api.kilo.ai/api/gateway", "model": "kilo-auto/free"})


def downgrade() -> None:
    # Deliberately non-destructive: experiment evidence is retained.
    pass
