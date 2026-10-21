"""Add processing queue, optional OCR, and draft integration records.

Revision ID: 20261021_04
Revises: 20261021_03
"""

from alembic import op
import sqlalchemy as sa

revision = "20261021_04"
down_revision = "20261021_03"
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    additions = {
        "provider_config_id": sa.Column("provider_config_id", sa.Integer()),
        "max_retries": sa.Column("max_retries", sa.Integer(), nullable=False, server_default="1"),
        "max_requests": sa.Column("max_requests", sa.Integer()),
        "max_tokens_budget": sa.Column("max_tokens_budget", sa.Integer()),
        "max_cost_budget": sa.Column("max_cost_budget", sa.Float()),
        "actual_requests": sa.Column("actual_requests", sa.Integer(), nullable=False, server_default="0"),
        "input_tokens": sa.Column("input_tokens", sa.Integer()),
        "output_tokens": sa.Column("output_tokens", sa.Integer()),
        "total_tokens": sa.Column("total_tokens", sa.Integer()),
        "actual_cost": sa.Column("actual_cost", sa.Float()),
        "average_response_time_ms": sa.Column("average_response_time_ms", sa.Float()),
        "force_reprocess": sa.Column("force_reprocess", sa.Boolean(), nullable=False, server_default=sa.false()),
        "created_at": sa.Column("created_at", sa.DateTime(timezone=True)),
        "updated_at": sa.Column("updated_at", sa.DateTime(timezone=True)),
    }
    if "processing_jobs" in tables:
        columns = _columns(inspector, "processing_jobs")
        provider_missing = "provider_config_id" not in columns
        with op.batch_alter_table("processing_jobs") as batch:
            for name, column in additions.items():
                if name not in columns:
                    batch.add_column(column)
            if provider_missing:
                batch.create_foreign_key(
                    "fk_processing_jobs_provider_config_id", "ai_provider_configs",
                    ["provider_config_id"], ["id"],
                )
        bind.execute(sa.text(
            "UPDATE processing_jobs SET created_at=COALESCE(created_at, started_at, CURRENT_TIMESTAMP), "
            "updated_at=COALESCE(updated_at, finished_at, started_at, CURRENT_TIMESTAMP)"
        ))

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "processing_job_items" not in tables:
        op.create_table(
            "processing_job_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_id", sa.Integer(), sa.ForeignKey("processing_jobs.id"), nullable=False),
            sa.Column("source_post_id", sa.Integer(), sa.ForeignKey("source_posts.id"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ai_test_run_id", sa.Integer(), sa.ForeignKey("ai_test_runs.id")),
            sa.Column("last_error_type", sa.String(100)), sa.Column("last_error_message", sa.Text()),
            sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("job_id", "source_post_id", name="uq_processing_job_post"),
        )
        op.create_index("ix_processing_job_items_job_id", "processing_job_items", ["job_id"])
        op.create_index("ix_processing_job_items_source_post_id", "processing_job_items", ["source_post_id"])
        op.create_index("ix_processing_job_items_status", "processing_job_items", ["status"])

    if "ocr_results" not in tables:
        op.create_table(
            "ocr_results",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_post_id", sa.Integer(), sa.ForeignKey("source_posts.id"), nullable=False),
            sa.Column("image_index", sa.Integer()), sa.Column("source_kind", sa.String(20), nullable=False),
            sa.Column("source_reference", sa.Text(), nullable=False), sa.Column("cached_image_path", sa.String(500)),
            sa.Column("engine", sa.String(50), nullable=False),
            sa.Column("languages", sa.String(100), nullable=False), sa.Column("status", sa.String(30), nullable=False),
            sa.Column("extracted_text", sa.Text()), sa.Column("corrected_text", sa.Text()),
            sa.Column("structured_suggestions", sa.JSON()), sa.Column("review_status", sa.String(30), nullable=False, server_default="unreviewed"),
            sa.Column("error_type", sa.String(100)), sa.Column("error_message", sa.Text()), sa.Column("duration_ms", sa.Float()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ocr_results_source_post_id", "ocr_results", ["source_post_id"])
        op.create_index("ix_ocr_results_status", "ocr_results", ["status"])

    if "aqarati_integration_config" not in tables:
        op.create_table(
            "aqarati_integration_config", sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("base_url", sa.String(500)), sa.Column("service_identity", sa.String(100), nullable=False, server_default="Aqarati Robot"),
            sa.Column("draft_path", sa.String(250), nullable=False, server_default="/api/robot/drafts"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("connection_status", sa.String(30), nullable=False, server_default="not_tested"), sa.Column("last_error", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "aqarati_sync_records" not in tables:
        op.create_table(
            "aqarati_sync_records", sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("listing_id", sa.Integer(), sa.ForeignKey("listing_drafts.id"), nullable=False),
            sa.Column("idempotency_key", sa.String(80), nullable=False), sa.Column("status", sa.String(30), nullable=False),
            sa.Column("remote_draft_id", sa.String(200)), sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("include_images", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("payload_snapshot", sa.JSON(), nullable=False),
            sa.Column("http_status", sa.Integer()), sa.Column("error_type", sa.String(100)), sa.Column("error_message", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_aqarati_sync_records_listing_id", "aqarati_sync_records", ["listing_id"])
        op.create_index("ix_aqarati_sync_records_idempotency_key", "aqarati_sync_records", ["idempotency_key"], unique=True)
        op.create_index("ix_aqarati_sync_records_status", "aqarati_sync_records", ["status"])


def downgrade() -> None:
    # Non-destructive by design: queued work, OCR reviews, and sync audit remain.
    pass
