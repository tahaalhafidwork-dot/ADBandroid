"""REST routes backed exclusively by the local SQLite database."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from pydantic import ValidationError

from .database import get_session
from .import_service import LegacyDataError, import_legacy_json
from .models import (
    AIProviderConfig, DialectTerm, ListingDraft, ModelUsage, ProcessingAttempt,
    ProcessingJob, ProviderRuntimeMetric, ReviewAction, SourcePost, SystemEvent,
)
from .schemas import (
    DialectTermCreate, DialectTermPatch, LegacyImportRequest, ListingPatch,
    ProviderSettings, ProviderSettingsPatch,
)
from .config import Settings

router = APIRouter(prefix="/api")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _page_meta(total: int, page: int, page_size: int) -> dict[str, int]:
    return {"total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


def _listing_dict(item: ListingDraft) -> dict[str, Any]:
    return {
        "id": item.id, "source_post_id": item.source_post_id, "listing_type": item.listing_type,
        "property_type": item.property_type, "title": item.title, "description": item.description,
        "price": item.price, "currency": item.currency, "area_sqm": item.area_sqm,
        "bedrooms": item.bedrooms, "bathrooms": item.bathrooms, "city": item.city,
        "district": item.district, "complex_name": item.complex_name, "floor": item.floor,
        "furnished": item.furnished, "confidence": item.confidence,
        "verification_status": item.verification_status, "review_status": item.review_status,
        "provider": item.provider, "model_name": item.model_name,
        "created_at": _iso(item.created_at), "updated_at": _iso(item.updated_at),
    }


@router.get("/health", tags=["system"])
def health(session: Session = Depends(get_session)):
    session.execute(select(1))
    return {"status": "ok", "database": "connected", "offline": True,
            "host": "127.0.0.1", "port": Settings.load().backend_port}


@router.get("/dashboard", tags=["dashboard"])
def dashboard(session: Session = Depends(get_session)):
    scalar = lambda statement: session.scalar(statement) or 0
    total = scalar(select(func.count(SourcePost.id)))
    unique_posts = scalar(select(func.count(SourcePost.id)).where(SourcePost.is_duplicate.is_(False)))
    processed = scalar(select(func.count(SourcePost.id)).where(SourcePost.processing_status.in_(["ok", "completed", "success"])))
    failed = scalar(select(func.count(SourcePost.id)).where(SourcePost.processing_status.in_(["failed", "error", "rejected"])))
    attempts = scalar(select(func.count(ProcessingAttempt.id)))
    actual_requests = session.scalar(select(func.sum(ModelUsage.request_count)).where(ModelUsage.metric_scope == "historical"))
    listings = scalar(select(func.count(ListingDraft.id)))
    json_errors = scalar(select(func.count(SourcePost.id)).where(SourcePost.has_json_error.is_(True)))
    truncated = scalar(select(func.count(SourcePost.id)).where(SourcePost.is_truncated.is_(True)))
    confirmed_duplicates = scalar(select(func.count(SourcePost.id)).where(SourcePost.duplicate_classification == "confirmed"))
    potential_rows = scalar(select(func.count(SourcePost.id)).where(SourcePost.duplicate_classification == "potential"))
    has_potential_history = session.scalar(select(func.count(SourcePost.id)).where(SourcePost.duplicate_classification == "potential"))
    categories = session.execute(select(SourcePost.category, func.count(SourcePost.id)).group_by(SourcePost.category)).all()
    states = session.execute(select(SourcePost.processing_status, func.count(SourcePost.id)).group_by(SourcePost.processing_status)).all()
    latest_ids = select(func.max(ProviderRuntimeMetric.id)).group_by(ProviderRuntimeMetric.provider_config_id)
    live_rows = session.scalars(select(ProviderRuntimeMetric).where(ProviderRuntimeMetric.id.in_(latest_ids))).all()

    def live_sum(field: str):
        values = [getattr(row, field) for row in live_rows if getattr(row, field) is not None]
        return sum(values) if values else None

    historical = {
        "imported_posts": total,
        "unique_imported_posts": unique_posts,
        "processed_successfully": processed,
        "failed_posts": failed,
        "processing_attempts": attempts,
        "actual_api_requests": actual_requests,
        "json_errors": json_errors,
        "truncated_responses": truncated,
        "unique_listing_drafts": listings,
        "confirmed_duplicates": confirmed_duplicates,
        # The legacy source has no separate potential-duplicate population.
        "potential_duplicates": potential_rows if has_potential_history else None,
    }
    live = {
        "request_count": live_sum("request_count"),
        "input_tokens": live_sum("input_tokens"),
        "output_tokens": live_sum("output_tokens"),
        "total_tokens": live_sum("total_tokens"),
        "connection_errors": live_sum("connection_errors"),
        "average_response_time_ms": None,
        "last_activity_at": max((row.last_activity_at for row in live_rows if row.last_activity_at), default=None),
    }
    response_time_values = [row.average_response_time_ms for row in live_rows if row.average_response_time_ms is not None]
    if response_time_values:
        live["average_response_time_ms"] = sum(response_time_values) / len(response_time_values)
    if live["last_activity_at"]:
        live["last_activity_at"] = _iso(live["last_activity_at"])
    return {
        "historical_import": historical,
        "live_monitoring": live,
        "category_distribution": [{"name": key or "غير مصنف", "value": count} for key, count in categories],
        "processing_distribution": [{"name": key or "غير معروف", "value": count} for key, count in states],
    }


@router.get("/posts", tags=["posts"])
def posts(
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=80),
    processing_status: str | None = Query(default=None, max_length=40),
    review_status: str | None = Query(default=None, max_length=40),
    sort: str = Query(default="imported_at"), order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(SourcePost).options(joinedload(SourcePost.listing)).outerjoin(SourcePost.listing)
    if search:
        term = "%{0}%".format(search.strip())
        statement = statement.where(or_(SourcePost.source_identifier.ilike(term), SourcePost.original_text.ilike(term), ListingDraft.city.ilike(term)))
    if category:
        statement = statement.where(SourcePost.category == category)
    if processing_status:
        statement = statement.where(SourcePost.processing_status == processing_status)
    if review_status:
        statement = statement.where(ListingDraft.review_status == review_status)
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = session.scalar(count_statement) or 0
    sort_columns = {"id": SourcePost.id, "published_at": SourcePost.published_at, "imported_at": SourcePost.imported_at,
                    "category": SourcePost.category, "city": ListingDraft.city}
    column = sort_columns.get(sort, SourcePost.imported_at)
    statement = statement.order_by((asc if order == "asc" else desc)(column)).offset((page - 1) * page_size).limit(page_size)
    rows = session.scalars(statement).unique().all()
    items = []
    for post in rows:
        items.append({"id": post.id, "source_identifier": post.source_identifier, "category": post.category,
                      "city": post.listing.city if post.listing else None, "published_at": _iso(post.published_at),
                      "image_count": len(post.image_urls) if post.image_urls is not None else None,
                      "processing_status": post.processing_status,
                      "review_status": post.listing.review_status if post.listing else None,
                      "source": post.source, "is_duplicate": post.is_duplicate})
    return {"items": items, **_page_meta(total, page, page_size)}


@router.get("/posts/{post_id}", tags=["posts"])
def post_detail(post_id: int, session: Session = Depends(get_session)):
    post = session.scalar(select(SourcePost).where(SourcePost.id == post_id).options(joinedload(SourcePost.listing), joinedload(SourcePost.attempts)))
    if not post:
        raise HTTPException(404, "المنشور غير موجود")
    return {
        "id": post.id, "source_identifier": post.source_identifier, "source": post.source,
        "source_url": post.source_url, "original_text": post.original_text,
        "published_at": _iso(post.published_at), "image_urls": post.image_urls,
        "category": post.category, "processing_status": post.processing_status,
        "rejection_reason": post.rejection_reason, "is_ambiguous": post.is_ambiguous,
        "has_json_error": post.has_json_error, "is_truncated": post.is_truncated,
        "is_duplicate": post.is_duplicate, "listing": _listing_dict(post.listing) if post.listing else None,
        "attempts": [{"id": a.id, "status": a.status, "provider": a.provider, "model_name": a.model_name,
                      "finish_reason": a.finish_reason, "error_type": a.error_type,
                      "error_message": a.error_message, "duration_ms": a.duration_ms,
                      "created_at": _iso(a.created_at)} for a in post.attempts],
    }


@router.get("/listings", tags=["listings"])
def listings(
    review_status: str | None = Query(default=None, max_length=40),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(ListingDraft).options(joinedload(ListingDraft.source_post)).order_by(desc(ListingDraft.updated_at))
    if review_status:
        statement = statement.where(ListingDraft.review_status == review_status)
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    rows = session.scalars(statement.offset((page - 1) * page_size).limit(page_size)).unique().all()
    items = []
    for item in rows:
        row = _listing_dict(item)
        row["original_text"] = item.source_post.original_text
        row["source_url"] = item.source_post.source_url
        row["image_urls"] = item.source_post.image_urls
        items.append(row)
    return {"items": items, **_page_meta(total, page, page_size)}


@router.patch("/listings/{listing_id}", tags=["listings"])
def update_listing(listing_id: int, payload: ListingPatch, session: Session = Depends(get_session)):
    item = session.get(ListingDraft, listing_id)
    if not item:
        raise HTTPException(404, "المسودة غير موجودة")
    changes = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        previous = getattr(item, key)
        if previous != value:
            changes[key] = {"before": previous, "after": value}
            setattr(item, key, value)
    if changes:
        session.add(ReviewAction(listing_id=item.id, action="updated", changes=changes))
        session.commit()
        session.refresh(item)
    return _listing_dict(item)


@router.get("/jobs", tags=["monitoring"])
def jobs(session: Session = Depends(get_session)):
    rows = session.scalars(select(ProcessingJob).order_by(desc(ProcessingJob.started_at))).all()
    return [{"id": row.id, "name": row.name, "status": row.status, "total_posts": row.total_posts,
             "completed_posts": row.completed_posts, "failed_posts": row.failed_posts,
             "started_at": _iso(row.started_at), "finished_at": _iso(row.finished_at), "errors": row.errors} for row in rows]


@router.get("/models/usage", tags=["monitoring"])
def model_usage(scope: str = Query(default="historical", pattern="^(historical|live)$"), session: Session = Depends(get_session)):
    rows = session.scalars(select(ModelUsage).where(ModelUsage.metric_scope == scope).order_by(desc(ModelUsage.recorded_at))).all()
    return [{"id": row.id, "provider": row.provider, "model_name": row.model_name,
             "request_count": row.request_count, "input_tokens": row.input_tokens,
             "output_tokens": row.output_tokens, "total_tokens": row.total_tokens,
             "response_time_ms": row.response_time_ms, "api_errors": row.api_errors,
             "json_errors": row.json_errors, "truncated_responses": row.truncated_responses,
             "actual_cost": row.actual_cost, "currency": row.currency,
             "recorded_at": _iso(row.recorded_at), "scope": row.metric_scope,
             "source_label": row.source_label} for row in rows]


def _provider_dict(row: AIProviderConfig) -> dict[str, Any]:
    return {"id": row.id, "provider_key": row.provider_key, "display_name": row.display_name,
            "api_base_url": row.api_base_url, "model_name": row.model_name,
            "is_enabled": row.is_enabled, "operation_mode": row.operation_mode,
            "max_tokens": row.max_tokens, "timeout_seconds": row.timeout_seconds,
            "request_limit": row.request_limit, "cost_cap": row.cost_cap,
            "connection_status": row.connection_status,
            "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}


@router.get("/models/providers", tags=["model-settings"])
def providers(session: Session = Depends(get_session)):
    return [_provider_dict(row) for row in session.scalars(select(AIProviderConfig).order_by(AIProviderConfig.id)).all()]


@router.patch("/models/providers/{provider_id}", tags=["model-settings"])
def update_provider(provider_id: int, payload: ProviderSettingsPatch, session: Session = Depends(get_session)):
    row = session.get(AIProviderConfig, provider_id)
    if not row:
        raise HTTPException(404, "المزود غير موجود")
    updates = payload.model_dump(exclude_unset=True)
    candidate = {
        "display_name": row.display_name, "api_base_url": row.api_base_url,
        "model_name": row.model_name, "is_enabled": row.is_enabled,
        "operation_mode": row.operation_mode, "max_tokens": row.max_tokens,
        "timeout_seconds": row.timeout_seconds, "request_limit": row.request_limit,
        "cost_cap": row.cost_cap, **updates,
    }
    try:
        validated = ProviderSettings.model_validate(candidate)
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    for key, value in validated.model_dump().items():
        setattr(row, key, value)
    # Editing never claims that a network connection was tested.
    row.connection_status = "not_tested"
    session.add(SystemEvent(event_type="provider_settings_updated", entity_type="ai_provider_config",
                            entity_id=row.id, details={"fields": sorted(updates)}))
    session.commit()
    session.refresh(row)
    return _provider_dict(row)


@router.get("/models/live", tags=["monitoring"])
def live_model_monitoring(session: Session = Depends(get_session)):
    provider_rows = session.scalars(select(AIProviderConfig).order_by(AIProviderConfig.id)).all()
    result = []
    for provider in provider_rows:
        metric = session.scalar(
            select(ProviderRuntimeMetric)
            .where(ProviderRuntimeMetric.provider_config_id == provider.id)
            .order_by(desc(ProviderRuntimeMetric.captured_at)).limit(1)
        )
        result.append({
            "provider": _provider_dict(provider),
            "metrics": None if metric is None else {
                "request_count": metric.request_count, "input_tokens": metric.input_tokens,
                "output_tokens": metric.output_tokens, "total_tokens": metric.total_tokens,
                "average_response_time_ms": metric.average_response_time_ms,
                "connection_errors": metric.connection_errors,
                "last_activity_at": _iso(metric.last_activity_at), "captured_at": _iso(metric.captured_at),
            },
        })
    return result


def _term_dict(row: DialectTerm):
    return {"id": row.id, "term": row.term, "meaning": row.meaning, "context": row.context,
            "usage_example": row.usage_example, "notes": row.notes,
            "approval_status": row.approval_status, "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at)}


@router.get("/dialect/terms", tags=["dialect"])
def dialect_terms(session: Session = Depends(get_session)):
    return [_term_dict(row) for row in session.scalars(select(DialectTerm).order_by(DialectTerm.term)).all()]


@router.post("/dialect/terms", status_code=status.HTTP_201_CREATED, tags=["dialect"])
def create_term(payload: DialectTermCreate, session: Session = Depends(get_session)):
    row = DialectTerm(**payload.model_dump())
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "المصطلح موجود مسبقاً") from exc
    session.refresh(row)
    return _term_dict(row)


@router.patch("/dialect/terms/{term_id}", tags=["dialect"])
def update_term(term_id: int, payload: DialectTermPatch, session: Session = Depends(get_session)):
    row = session.get(DialectTerm, term_id)
    if not row:
        raise HTTPException(404, "المصطلح غير موجود")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "المصطلح موجود مسبقاً") from exc
    session.refresh(row)
    return _term_dict(row)


@router.post("/imports/legacy", tags=["imports"])
def import_legacy(payload: LegacyImportRequest, session: Session = Depends(get_session)):
    try:
        return import_legacy_json(session, payload.source)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except LegacyDataError as exc:
        raise HTTPException(422, str(exc)) from exc
