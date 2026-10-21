"""Relational data model for the local lab."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourcePost(Base):
    __tablename__ = "source_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_identifier: Mapped[str | None] = mapped_column(String(500), index=True)
    source_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    image_urls: Mapped[list[str] | None] = mapped_column(JSON)
    category: Mapped[str | None] = mapped_column(String(80), index=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False)
    has_json_error: Mapped[bool] = mapped_column(Boolean, default=False)
    is_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_classification: Mapped[str | None] = mapped_column(String(30), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    listing: Mapped["ListingDraft | None"] = relationship(back_populates="source_post", uselist=False)
    attempts: Mapped[list["ProcessingAttempt"]] = relationship(back_populates="source_post")


class ListingDraft(Base):
    __tablename__ = "listing_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id"), unique=True, index=True)
    listing_type: Mapped[str | None] = mapped_column(String(50), index=True)
    property_type: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(20))
    area_sqm: Mapped[float | None] = mapped_column(Float)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    bathrooms: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    district: Mapped[str | None] = mapped_column(String(160))
    complex_name: Mapped[str | None] = mapped_column(String(160))
    floor: Mapped[str | None] = mapped_column(String(80))
    furnished: Mapped[bool | None] = mapped_column(Boolean)
    confidence: Mapped[float | None] = mapped_column(Float)
    verification_status: Mapped[str] = mapped_column(String(40), default="unverified")
    review_status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    provider: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source_post: Mapped[SourcePost] = relationship(back_populates="listing")
    review_actions: Mapped[list["ReviewAction"]] = relationship(back_populates="listing")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), index=True)
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    completed_posts: Mapped[int] = mapped_column(Integer, default=0)
    failed_posts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    errors: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
    provider_config_id: Mapped[int | None] = mapped_column(ForeignKey("ai_provider_configs.id"), index=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=1)
    max_requests: Mapped[int | None] = mapped_column(Integer)
    max_tokens_budget: Mapped[int | None] = mapped_column(Integer)
    max_cost_budget: Mapped[float | None] = mapped_column(Float)
    actual_requests: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    actual_cost: Mapped[float | None] = mapped_column(Float)
    average_response_time_ms: Mapped[float | None] = mapped_column(Float)
    force_reprocess: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    items: Mapped[list["ProcessingJobItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ProcessingJobItem(Base):
    __tablename__ = "processing_job_items"
    __table_args__ = (UniqueConstraint("job_id", "source_post_id", name="uq_processing_job_post"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("processing_jobs.id"), index=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    position: Mapped[int] = mapped_column(Integer)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_test_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_test_runs.id"))
    last_error_type: Mapped[str | None] = mapped_column(String(100))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job: Mapped[ProcessingJob] = relationship(back_populates="items")


class ProcessingAttempt(Base):
    __tablename__ = "processing_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id"), index=True)
    status: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(150))
    finish_reason: Mapped[str | None] = mapped_column(String(100))
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source_post: Mapped[SourcePost] = relationship(back_populates="attempts")


class ModelUsage(Base):
    __tablename__ = "model_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
    provider: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(150))
    request_count: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[float | None] = mapped_column(Float)
    api_errors: Mapped[int | None] = mapped_column(Integer)
    json_errors: Mapped[int | None] = mapped_column(Integer)
    truncated_responses: Mapped[int | None] = mapped_column(Integer)
    actual_cost: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(10))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metric_scope: Mapped[str] = mapped_column(String(20), default="historical", index=True)
    source_label: Mapped[str | None] = mapped_column(String(100))


class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    api_base_url: Mapped[str] = mapped_column(String(500))
    model_name: Mapped[str | None] = mapped_column(String(200))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    operation_mode: Mapped[str] = mapped_column(String(20))
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    request_limit: Mapped[int | None] = mapped_column(Integer)
    cost_cap: Mapped[float | None] = mapped_column(Float)
    connection_status: Mapped[str] = mapped_column(String(30), default="not_tested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    runtime_metrics: Mapped[list["ProviderRuntimeMetric"]] = relationship(back_populates="provider")
    test_runs: Mapped[list["AITestRun"]] = relationship(back_populates="provider")


class ProviderRuntimeMetric(Base):
    __tablename__ = "provider_runtime_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_config_id: Mapped[int] = mapped_column(ForeignKey("ai_provider_configs.id"), index=True)
    request_count: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    average_response_time_ms: Mapped[float | None] = mapped_column(Float)
    connection_errors: Mapped[int | None] = mapped_column(Integer)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    provider: Mapped[AIProviderConfig] = relationship(back_populates="runtime_metrics")


class AITestRun(Base):
    """Immutable result of one explicitly confirmed single-post experiment."""

    __tablename__ = "ai_test_runs"
    __table_args__ = (
        Index(
            "uq_ai_test_one_active",
            "active_slot",
            unique=True,
            sqlite_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id"), index=True)
    provider_config_id: Mapped[int] = mapped_column(ForeignKey("ai_provider_configs.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    preview_fingerprint: Mapped[str] = mapped_column(String(64))
    active_slot: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    requested_model: Mapped[str] = mapped_column(String(200))
    actual_model: Mapped[str | None] = mapped_column(String(200))
    confirmed_external_send: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_data_handling: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_unknown_cost: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    http_status: Mapped[int | None] = mapped_column(Integer)
    finish_reason: Mapped[str | None] = mapped_column(String(100))
    json_status: Mapped[str] = mapped_column(String(30), default="not_checked")
    schema_status: Mapped[str] = mapped_column(String(30), default="not_checked")
    failure_type: Mapped[str | None] = mapped_column(String(100))
    failure_message: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    actual_cost: Mapped[float | None] = mapped_column(Float)
    cost_currency: Mapped[str | None] = mapped_column(String(10))
    cost_status: Mapped[str] = mapped_column(String(30), default="unavailable")
    extracted_result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    prompt_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    redacted_input: Mapped[str] = mapped_column(Text)
    raw_response_redacted: Mapped[str | None] = mapped_column(Text)
    raw_response_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_status: Mapped[str] = mapped_column(String(30), default="unreviewed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source_post: Mapped[SourcePost] = relationship()
    provider: Mapped[AIProviderConfig] = relationship(back_populates="test_runs")
    reviews: Mapped[list["AITestReview"]] = relationship(back_populates="test_run")


class AITestReview(Base):
    __tablename__ = "ai_test_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    ai_test_run_id: Mapped[int] = mapped_column(ForeignKey("ai_test_runs.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text)
    suggested_term: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    test_run: Mapped[AITestRun] = relationship(back_populates="reviews")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id"), index=True)
    image_index: Mapped[int | None] = mapped_column(Integer)
    source_kind: Mapped[str] = mapped_column(String(20))
    source_reference: Mapped[str] = mapped_column(Text)
    cached_image_path: Mapped[str | None] = mapped_column(String(500))
    engine: Mapped[str] = mapped_column(String(50))
    languages: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), index=True)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    corrected_text: Mapped[str | None] = mapped_column(Text)
    structured_suggestions: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(30), default="unreviewed")
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AqaratiIntegrationConfig(Base):
    __tablename__ = "aqarati_integration_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_url: Mapped[str | None] = mapped_column(String(500))
    service_identity: Mapped[str] = mapped_column(String(100), default="Aqarati Robot")
    draft_path: Mapped[str] = mapped_column(String(250), default="/api/robot/drafts")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    connection_status: Mapped[str] = mapped_column(String(30), default="not_tested")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AqaratiSyncRecord(Base):
    __tablename__ = "aqarati_sync_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listing_drafts.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    remote_draft_id: Mapped[str | None] = mapped_column(String(200))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    include_images: Mapped[bool] = mapped_column(Boolean, default=False)
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DialectTerm(Base):
    __tablename__ = "dialect_terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(120), unique=True)
    meaning: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text)
    usage_example: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    approval_status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listing_drafts.id"), index=True)
    action: Mapped[str] = mapped_column(String(50))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    actor: Mapped[str] = mapped_column(String(100), default="local_admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listing: Mapped[ListingDraft] = relationship(back_populates="review_actions")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(250))
    source_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(40))
    accepted_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    rejection_reasons: Mapped[dict[str, int] | None] = mapped_column(JSON)
    source_stats: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemEvent(Base):
    __tablename__ = "system_events"
    __table_args__ = (UniqueConstraint("event_type", "entity_type", "entity_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
