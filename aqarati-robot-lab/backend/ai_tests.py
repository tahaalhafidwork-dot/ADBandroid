"""Local control-plane routes for one privacy-redacted cloud experiment."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .config import Settings
from .database import get_session
from .models import (
    AIProviderConfig, AITestReview, AITestRun, DialectTerm, ListingDraft,
    ProviderRuntimeMetric, SourcePost,
)
from .processing.privacy import redact_personal_data, redact_secrets
from .processing.prompt import build_prompt
from .processing.schemas import OutputParseError, parse_extraction_output
from .providers.base import AIProvider, ProviderFailure, ProviderRequest, ProviderResponse
from .providers.kilo import KiloProvider, validate_kilo_base_url
from .providers.local import LocalOpenAIProvider, validate_local_base_url
from .schemas import AITestPreviewRequest, AITestReviewRequest, AITestRunRequest

router = APIRouter(prefix="/api/ai-tests", tags=["ai-test-lab"])
RAW_RESPONSE_LIMIT = 32_768
RAW_RESPONSE_RETENTION = timedelta(days=7)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _provider_factory(config: AIProviderConfig, api_key: str) -> AIProvider:
    if config.provider_key == "kilo":
        return KiloProvider(config.api_base_url, api_key)
    if config.provider_key in {"ollama", "openvino"}:
        return LocalOpenAIProvider(config.api_base_url, config.provider_key)
    raise ValueError("unsupported AI provider")


def get_ai_provider_factory() -> Callable[[AIProviderConfig, str], AIProvider]:
    """FastAPI dependency replaced with an in-memory mock by every automated test."""
    return _provider_factory


def _approved_terms(session: Session) -> list[dict[str, str]]:
    rows = session.scalars(
        select(DialectTerm).where(DialectTerm.approval_status == "approved").order_by(DialectTerm.term)
    ).all()
    return [{"term": row.term, "meaning": row.meaning, "context": row.context or ""} for row in rows]


def _load_subject(session: Session, post_id: int, provider_key: str = "kilo") -> tuple[SourcePost, AIProviderConfig, str, list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    post = session.get(SourcePost, post_id)
    if not post:
        raise HTTPException(404, "المنشور غير موجود")
    if not post.original_text or not post.original_text.strip():
        raise HTTPException(422, "النص الأصلي غير متوفر؛ لا يمكن تشغيل الاختبار")
    provider = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == provider_key))
    if not provider:
        raise HTTPException(409, "إعداد المزود غير موجود")
    redacted = redact_personal_data(post.original_text)
    terms = _approved_terms(session)
    messages, prompt_snapshot = build_prompt(redacted, terms)
    safe_settings = {
        "provider_key": provider.provider_key,
        "api_base_url": provider.api_base_url,
        "model_name": provider.model_name,
        "max_tokens": provider.max_tokens,
        "timeout_seconds": provider.timeout_seconds,
        "request_limit": provider.request_limit,
        "cost_cap": provider.cost_cap,
    }
    prompt_snapshot["provider_settings"] = safe_settings
    prompt_snapshot["redacted_input_sha256"] = hashlib.sha256(redacted.encode("utf-8")).hexdigest()
    fingerprint_payload = {"post_id": post.id, "redacted": redacted, "snapshot": prompt_snapshot}
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return post, provider, redacted, messages, prompt_snapshot, {"fingerprint": fingerprint, "terms": terms}


def _guards(provider: AIProviderConfig) -> list[dict[str, Any]]:
    settings = Settings.load()
    model_name = (provider.model_name or "").strip()
    checks = [
        ("provider_enabled", provider.is_enabled, "المزود مفعّل"),
        ("model_selected", bool(provider.model_name and provider.model_name.strip()), "تم اختيار نموذج"),
    ]
    if provider.operation_mode == "cloud":
        key_present = bool(os.environ.get("KILO_API_KEY", "").strip())
        is_explicitly_free = model_name == "kilo-auto/free" or model_name.endswith(":free")
        checks.extend([
            ("cloud_test_switch", settings.enable_cloud_ai_test, "إذن اختبار السحابة مفعّل"),
            ("online_mode", not settings.offline, "وضع عدم الاتصال معطّل"),
            ("credential_present", key_present, "مفتاح KILO_API_KEY موجود في البيئة"),
            ("free_model_policy", is_explicitly_free, "النموذج مجاني صراحة وفق السياسة"),
        ])
        try: validate_kilo_base_url(provider.api_base_url); url_valid = True
        except ValueError: url_valid = False
        checks.append(("official_endpoint", url_valid, "عنوان Kilo رسمي وآمن"))
    else:
        try: validate_local_base_url(provider.api_base_url); url_valid = True
        except ValueError: url_valid = False
        checks.append(("loopback_endpoint", url_valid, "عنوان المزود محلي loopback"))
    return [{"key": key, "ok": bool(ok), "label": label} for key, ok, label in checks]


def _old_listing(row: ListingDraft | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = (
        "listing_type", "property_type", "title", "description", "price", "currency", "area_sqm",
        "bedrooms", "bathrooms", "city", "district", "complex_name", "floor", "furnished", "confidence",
    )
    return {key: getattr(row, key) for key in keys}


def _review_dict(row: AITestReview) -> dict[str, Any]:
    return {"id": row.id, "action": row.action, "note": row.note,
            "suggested_term": row.suggested_term, "created_at": _iso(row.created_at)}


def _run_dict(row: AITestRun) -> dict[str, Any]:
    return {
        "id": row.id, "post_id": row.source_post_id, "provider_id": row.provider_config_id,
        "idempotency_key": row.idempotency_key, "status": row.status,
        "requested_model": row.requested_model, "actual_model": row.actual_model,
        "started_at": _iso(row.started_at), "finished_at": _iso(row.finished_at),
        "duration_ms": row.duration_ms, "http_status": row.http_status,
        "finish_reason": row.finish_reason, "json_status": row.json_status,
        "schema_status": row.schema_status, "failure_type": row.failure_type,
        "failure_message": row.failure_message, "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens, "total_tokens": row.total_tokens,
        "actual_cost": row.actual_cost, "cost_currency": row.cost_currency,
        "cost_status": row.cost_status, "result": row.extracted_result,
        "redacted_input": row.redacted_input, "review_status": row.review_status,
        "historical_listing": _old_listing(row.source_post.listing if row.source_post else None),
        "reviews": [_review_dict(review) for review in row.reviews],
        "raw_response_expires_at": _iso(row.raw_response_expires_at),
        "created_at": _iso(row.created_at),
    }


def _purge_expired_raw_responses(session: Session) -> None:
    expired = session.scalars(
        select(AITestRun).where(
            AITestRun.raw_response_redacted.is_not(None),
            AITestRun.raw_response_expires_at.is_not(None),
            AITestRun.raw_response_expires_at <= _utcnow(),
        )
    ).all()
    for row in expired:
        row.raw_response_redacted = None
        row.raw_response_expires_at = None
    if expired:
        session.commit()


@router.post("/preview")
def preview(payload: AITestPreviewRequest, session: Session = Depends(get_session)):
    post, provider, redacted, _messages, _snapshot, extra = _load_subject(session, payload.post_id, payload.provider_key)
    guards = _guards(provider)
    return {
        "post_id": post.id,
        "original_text": post.original_text,
        "redacted_text": redacted,
        "preview_fingerprint": extra["fingerprint"],
        "provider": {"id": provider.id, "name": provider.display_name, "model": provider.model_name},
        "guards": guards,
        "ready": all(item["ok"] for item in guards),
        "warnings": ([
            "سيُرسل النص المنقح إلى مزود سحابي خارجي بعد التأكيد فقط.",
            "قد يوجّه kilo-auto/free الطلب إلى مزود يحتفظ بالمدخلات والمخرجات؛ لا ترسل بيانات شخصية أو سرية.",
            "التكلفة قبل الطلب غير مؤكدة، ولن تعرض كصفر ما لم يؤكدها رد المزود.",
            "لا تُرسل الصور أو رابط المصدر أو النص الأصلي.",
        ] if provider.operation_mode == "cloud" else [
            "سيُرسل النص المنقح إلى خادم محلي على loopback فقط.",
            "لن يبدأ المختبر الخادم المحلي ولن ينزّل نموذجًا.",
            "لا تُرسل الصور أو رابط المصدر أو النص الأصلي.",
        ]),
    }


def _assert_run_allowed(session: Session, provider: AIProviderConfig, payload: AITestRunRequest) -> str:
    guards = _guards(provider)
    failed = [item["label"] for item in guards if not item["ok"]]
    if failed:
        raise HTTPException(409, "تعذر التشغيل: " + "، ".join(failed))
    if provider.operation_mode == "cloud" and not (payload.confirmed_external_send and payload.accepted_data_handling and payload.accepted_unknown_cost):
        raise HTTPException(422, "يلزم تأكيد الإرسال الخارجي وسياسة البيانات وعدم يقين التكلفة")
    count = session.scalar(select(func.count(AITestRun.id)).where(AITestRun.provider_config_id == provider.id)) or 0
    if provider.request_limit is not None and count >= provider.request_limit:
        raise HTTPException(409, "تم بلوغ حد الطلبات المضبوط للمزود")
    return os.environ["KILO_API_KEY"] if provider.operation_mode == "cloud" else ""


def _latest_metric(session: Session, provider_id: int) -> ProviderRuntimeMetric | None:
    return session.scalar(
        select(ProviderRuntimeMetric).where(ProviderRuntimeMetric.provider_config_id == provider_id)
        .order_by(desc(ProviderRuntimeMetric.captured_at)).limit(1)
    )


def _token_total(previous: int | None, current: int | None, had_previous: bool) -> int | None:
    if current is None or (had_previous and previous is None):
        return None
    return (previous or 0) + current


def _record_metric(session: Session, provider: AIProviderConfig, *, response: ProviderResponse | None,
                   failure: ProviderFailure | None) -> None:
    previous = _latest_metric(session, provider.id)
    had_previous = previous is not None
    previous_count = previous.request_count or 0 if previous else 0
    request_count = previous_count + 1
    errors = (previous.connection_errors or 0 if previous else 0) + (1 if failure else 0)
    duration = response.duration_ms if response else failure.duration_ms if failure else None
    if duration is None or (had_previous and previous.average_response_time_ms is None):
        average_duration = None
    else:
        previous_average = previous.average_response_time_ms if previous else 0
        average_duration = (((previous_average or 0) * previous_count) + duration) / request_count
    session.add(ProviderRuntimeMetric(
        provider_config_id=provider.id,
        request_count=request_count,
        input_tokens=_token_total(previous.input_tokens if previous else None, response.input_tokens if response else None, had_previous),
        output_tokens=_token_total(previous.output_tokens if previous else None, response.output_tokens if response else None, had_previous),
        total_tokens=_token_total(previous.total_tokens if previous else None, response.total_tokens if response else None, had_previous),
        average_response_time_ms=average_duration,
        connection_errors=errors,
        last_activity_at=_utcnow(),
    ))


@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_test(
    payload: AITestRunRequest,
    session: Session = Depends(get_session),
    factory: Callable[[AIProviderConfig, str], AIProvider] = Depends(get_ai_provider_factory),
):
    existing = session.execute(
        select(AITestRun).where(AITestRun.idempotency_key == payload.idempotency_key)
        .options(joinedload(AITestRun.source_post).joinedload(SourcePost.listing), joinedload(AITestRun.reviews))
    ).unique().scalar_one_or_none()
    if existing:
        if existing.source_post_id != payload.post_id:
            raise HTTPException(409, "مفتاح منع التكرار مستخدم لمنشور آخر")
        return _run_dict(existing)
    post, provider, redacted, messages, snapshot, extra = _load_subject(session, payload.post_id, payload.provider_key)
    if payload.preview_fingerprint != extra["fingerprint"]:
        raise HTTPException(409, "المعاينة قديمة؛ أعد المعاينة قبل التشغيل")
    api_key = _assert_run_allowed(session, provider, payload)
    row = AITestRun(
        source_post_id=post.id, provider_config_id=provider.id,
        idempotency_key=payload.idempotency_key, preview_fingerprint=payload.preview_fingerprint,
        status="running", requested_model=provider.model_name or "",
        confirmed_external_send=payload.confirmed_external_send,
        accepted_data_handling=payload.accepted_data_handling,
        accepted_unknown_cost=payload.accepted_unknown_cost,
        prompt_snapshot=snapshot, redacted_input=redacted,
    )
    session.add(row)
    try:
        session.commit()  # Claim the global active slot before the one external request.
    except IntegrityError as exc:
        session.rollback()
        race = session.scalar(select(AITestRun).where(AITestRun.idempotency_key == payload.idempotency_key))
        if race:
            session.refresh(race)
            return _run_dict(race)
        raise HTTPException(409, "يوجد اختبار نشط؛ انتظر اكتماله") from exc
    session.refresh(row)

    response: ProviderResponse | None = None
    failure: ProviderFailure | None = None
    request_attempted = False
    try:
        provider_client = factory(provider, api_key)
        request_attempted = True
        response = provider_client.complete(ProviderRequest(
            model=row.requested_model, messages=messages,
            max_tokens=provider.max_tokens, timeout_seconds=provider.timeout_seconds,
        ))
        row.http_status = response.http_status
        row.actual_model = response.actual_model
        row.finish_reason = response.finish_reason
        row.duration_ms = response.duration_ms
        row.input_tokens = response.input_tokens
        row.output_tokens = response.output_tokens
        row.total_tokens = response.total_tokens
        row.actual_cost = response.actual_cost
        row.cost_currency = response.cost_currency
        row.cost_status = "confirmed_zero" if response.actual_cost == 0 else "reported" if response.actual_cost is not None else "unavailable"
        row.raw_response_redacted = redact_secrets(response.raw_body or response.content, (api_key,))[:RAW_RESPONSE_LIMIT]
        row.raw_response_expires_at = _utcnow() + RAW_RESPONSE_RETENTION
        try:
            parsed = parse_extraction_output(response.content, response.finish_reason)
            row.extracted_result = parsed.model_dump(mode="json")
            row.json_status = "valid"
            row.schema_status = "valid"
            row.status = "succeeded"
        except OutputParseError as exc:
            row.status = "failed"
            row.json_status = "truncated" if exc.truncated else "invalid" if "json" in exc.kind else "valid"
            row.schema_status = "invalid" if exc.kind == "invalid_schema" else "not_checked"
            row.failure_type = exc.kind
            row.failure_message = "تعذر قبول خرج النموذج وفق العقد الصارم"
        if (response.actual_cost is not None and provider.cost_cap is not None
                and response.actual_cost > provider.cost_cap):
            row.status = "failed"
            row.cost_status = "cap_exceeded"
            row.failure_type = "cost_cap_exceeded"
            row.failure_message = "التكلفة المبلغ عنها تجاوزت سقف المزود"
        provider.connection_status = "connected"
    except ProviderFailure as exc:
        failure = exc
        row.status = "failed"
        row.http_status = exc.http_status
        row.duration_ms = exc.duration_ms
        row.failure_type = exc.kind
        row.failure_message = str(exc)
        row.raw_response_redacted = redact_secrets(exc.raw_body or "", (api_key,))[:RAW_RESPONSE_LIMIT] or None
        row.raw_response_expires_at = _utcnow() + RAW_RESPONSE_RETENTION if row.raw_response_redacted else None
        provider.connection_status = "failed"
    except (ValueError, TypeError) as exc:
        failure = ProviderFailure("provider_configuration", "تعذر إنشاء مزود Kilo")
        row.status = "failed"
        row.failure_type = failure.kind
        row.failure_message = str(failure)
        provider.connection_status = "failed"
    finally:
        row.finished_at = _utcnow()
        if request_attempted:
            _record_metric(session, provider, response=response, failure=failure)
        session.commit()
    loaded = session.execute(
        select(AITestRun).where(AITestRun.id == row.id)
        .options(joinedload(AITestRun.source_post).joinedload(SourcePost.listing), joinedload(AITestRun.reviews))
    ).unique().scalar_one()
    return _run_dict(loaded)


@router.get("")
def list_tests(post_id: int | None = Query(default=None, gt=0), session: Session = Depends(get_session)):
    _purge_expired_raw_responses(session)
    statement = select(AITestRun).options(
        joinedload(AITestRun.source_post).joinedload(SourcePost.listing), joinedload(AITestRun.reviews)
    ).order_by(desc(AITestRun.created_at))
    if post_id is not None:
        statement = statement.where(AITestRun.source_post_id == post_id)
    return [_run_dict(row) for row in session.scalars(statement).unique().all()]


@router.get("/{test_id}")
def get_test(test_id: int, session: Session = Depends(get_session)):
    _purge_expired_raw_responses(session)
    row = session.execute(
        select(AITestRun).where(AITestRun.id == test_id)
        .options(joinedload(AITestRun.source_post).joinedload(SourcePost.listing), joinedload(AITestRun.reviews))
    ).unique().scalar_one_or_none()
    if not row:
        raise HTTPException(404, "الاختبار غير موجود")
    return _run_dict(row)


@router.post("/{test_id}/review", status_code=status.HTTP_201_CREATED)
def review_test(test_id: int, payload: AITestReviewRequest, session: Session = Depends(get_session)):
    row = session.get(AITestRun, test_id)
    if not row:
        raise HTTPException(404, "الاختبار غير موجود")
    review = AITestReview(
        ai_test_run_id=row.id, action=payload.action,
        note=payload.note.strip() if payload.note else None,
        suggested_term=payload.suggested_term.strip() if payload.suggested_term else None,
    )
    session.add(review)
    if payload.action == "accept_for_test":
        row.review_status = "accepted_for_test"
    elif payload.action == "reject":
        row.review_status = "rejected"
    session.commit()
    session.refresh(review)
    return _review_dict(review)
