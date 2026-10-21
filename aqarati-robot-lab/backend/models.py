"""Relational data model for the local lab."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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

