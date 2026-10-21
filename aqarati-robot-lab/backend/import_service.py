"""Validate and ingest supported legacy JSON shapes into SQLite."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import paths
from .config import Settings
from .models import (
    ImportBatch,
    ListingDraft,
    ModelUsage,
    ProcessingAttempt,
    ProcessingJob,
    SourcePost,
    SystemEvent,
)

MAX_IMPORT_BYTES = 25 * 1024 * 1024
ALLOWED_NAMES = {"aqarati_50_results.json", "aqarati_50_results"}


class LegacyDataError(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_source(name: str) -> Path:
    if name not in ALLOWED_NAMES or Path(name).name != name:
        raise LegacyDataError("مصدر الاستيراد غير مسموح")
    settings = Settings.load()
    candidates = [settings.legacy_dir / name]
    if name.endswith(".json"):
        candidates.append(settings.legacy_dir / name.removesuffix(".json"))
    candidates.append(paths.repo_path("real_estate_ai_pipeline", "output", "aqarati_50_results.json"))
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            if paths.is_inside(resolved, settings.legacy_dir):
                return resolved
            allowed_root = paths.repo_path("real_estate_ai_pipeline", "output").resolve()
            if paths.is_inside(resolved, allowed_root):
                return resolved
    raise FileNotFoundError("ملف البيانات القديمة غير موجود محلياً")


def _parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_number(value: Any, *, integer: bool = False):
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value) if integer else float(value)
    except (TypeError, ValueError):
        return None


def _records(payload: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], [], [], {}
    if not isinstance(payload, dict):
        raise LegacyDataError("جذر JSON يجب أن يكون كائناً أو قائمة")
    accepted = payload.get("structured_listings", payload.get("listings", payload.get("results", [])))
    rejected = payload.get("rejected_posts", payload.get("rejected", []))
    duplicates = payload.get("duplicates", [])
    stats = payload.get("stats", {})
    for label, value in (("structured_listings", accepted), ("rejected_posts", rejected), ("duplicates", duplicates)):
        if not isinstance(value, list):
            raise LegacyDataError("الحقل {0} يجب أن يكون قائمة".format(label))
    return (
        [item for item in accepted if isinstance(item, dict)],
        [item for item in rejected if isinstance(item, dict)],
        [item for item in duplicates if isinstance(item, dict)],
        stats if isinstance(stats, dict) else {},
    )


def _post_fingerprint(item: dict[str, Any], group: str, index: int) -> str:
    identity = item.get("source_url") or item.get("url") or item.get("id")
    if identity is None:
        identity = "{0}:{1}:{2}".format(group, index, item.get("text", ""))
    return _sha256(str(identity).strip().encode("utf-8"))


def _category(item: dict[str, Any]) -> str | None:
    return item.get("listing_type") or item.get("category")


def _processing_flags(item: dict[str, Any], rejected: bool) -> tuple[str, bool, bool, bool]:
    status = str(item.get("_status") or item.get("status") or ("failed" if rejected else "completed"))
    reason = str(item.get("reason") or "").lower()
    json_error = any(marker in reason for marker in ("json", "parse", "extraction failed")) or "json" in status.lower()
    truncated = bool(item.get("_truncated")) or "truncated" in reason or "truncated" in str(item.get("finish_reason", "")).lower()
    ambiguous = _category(item) in {None, "unclear", "ambiguous"}
    if rejected and status not in {"failed", "error", "rejected"}:
        status = "rejected"
    return status, ambiguous, json_error, truncated


def _add_post(session: Session, batch_id: int, item: dict[str, Any], group: str, index: int) -> tuple[bool, SourcePost | None]:
    fingerprint = _post_fingerprint(item, group, index)
    if session.scalar(select(SourcePost.id).where(SourcePost.source_fingerprint == fingerprint)):
        return False, None
    rejected = group == "rejected"
    status, ambiguous, json_error, truncated = _processing_flags(item, rejected)
    image_urls = item.get("image_urls") or item.get("images")
    if not isinstance(image_urls, list):
        image_urls = None
    source_url = item.get("source_url") or item.get("url")
    post = SourcePost(
        source_identifier=str(source_url or item.get("id") or "{0}-{1}".format(group, index)),
        source_fingerprint=fingerprint,
        source=item.get("source"),
        source_url=source_url,
        original_text=item.get("text"),
        published_at=_parse_datetime(item.get("published_at")),
        image_urls=image_urls,
        category=_category(item),
        processing_status=status,
        rejection_reason=item.get("reason"),
        is_ambiguous=ambiguous,
        has_json_error=json_error,
        is_truncated=truncated,
        is_duplicate=group == "duplicate",
        duplicate_classification="confirmed" if group == "duplicate" else None,
        import_batch_id=batch_id,
        raw_payload=item,
    )
    session.add(post)
    session.flush()
    # Duplicate candidates remain visible as source posts, but deliberately do
    # not become a second editable listing draft.
    if group == "accepted":
        session.add(ListingDraft(
            source_post_id=post.id,
            listing_type=item.get("listing_type"),
            property_type=item.get("property_type"),
            title=item.get("title"),
            description=item.get("description"),
            price=_as_number(item.get("price")),
            currency=item.get("currency"),
            area_sqm=_as_number(item.get("area_sqm")),
            bedrooms=_as_number(item.get("bedrooms"), integer=True),
            bathrooms=_as_number(item.get("bathrooms"), integer=True),
            city=item.get("city"),
            district=item.get("district"),
            complex_name=item.get("complex_name"),
            floor=str(item["floor"]) if item.get("floor") is not None else None,
            furnished=item.get("furnished") if isinstance(item.get("furnished"), bool) else None,
            confidence=_as_number(item.get("confidence")),
            provider=item.get("_provider"),
            model_name=item.get("_model"),
            review_status="needs_review" if ambiguous else "draft",
        ))
    session.add(ProcessingAttempt(
        source_post_id=post.id,
        status=status,
        provider=item.get("_provider"),
        model_name=item.get("_model"),
        finish_reason=item.get("_finish_reason") or item.get("finish_reason"),
        error_type="json" if json_error else ("rejected" if rejected else None),
        error_message=str(item.get("reason"))[:500] if item.get("reason") else None,
    ))
    return True, post


def _add_usage(session: Session, batch_id: int, stats: dict[str, Any]) -> None:
    cost = stats.get("cost_summary") if isinstance(stats.get("cost_summary"), dict) else {}
    timing = stats.get("timing") if isinstance(stats.get("timing"), dict) else {}
    truncated = stats.get("truncated_responses")
    parse_errors = stats.get("parse_errors")
    if not cost and not stats.get("provider"):
        return
    session.add(ModelUsage(
        import_batch_id=batch_id,
        provider=str(cost.get("provider") or stats.get("provider") or "غير معروف"),
        model_name=cost.get("model"),
        request_count=_as_number(cost.get("requests"), integer=True),
        input_tokens=_as_number(cost.get("prompt_tokens"), integer=True),
        output_tokens=_as_number(cost.get("completion_tokens"), integer=True),
        total_tokens=_as_number(cost.get("total_tokens"), integer=True),
        response_time_ms=(_as_number(timing.get("total_seconds")) or 0) * 1000 if timing.get("total_seconds") is not None else None,
        api_errors=None,
        json_errors=len(parse_errors) if isinstance(parse_errors, list) else None,
        truncated_responses=len(truncated) if isinstance(truncated, list) else None,
        actual_cost=_as_number(cost.get("estimated_cost_usd")),
        currency="USD" if cost.get("estimated_cost_usd") is not None else None,
        metric_scope="historical",
        source_label="legacy_import",
    ))


def import_legacy_json(session: Session, source_name: str = "aqarati_50_results.json") -> dict[str, Any]:
    source = _safe_source(source_name)
    if source.stat().st_size > MAX_IMPORT_BYTES:
        raise LegacyDataError("ملف الاستيراد أكبر من الحد المسموح")
    raw = source.read_bytes()
    digest = _sha256(raw)
    existing = session.scalar(select(ImportBatch).where(ImportBatch.source_fingerprint == digest))
    if existing:
        return {"batch_id": existing.id, "status": "already_imported", "accepted": existing.accepted_count,
                "rejected": existing.rejected_count, "duplicates": existing.duplicate_count,
                "rejection_reasons": existing.rejection_reasons or {}}
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LegacyDataError("ملف JSON غير صالح: {0}".format(exc)) from exc
    accepted, rejected, duplicates, stats = _records(payload)
    batch = ImportBatch(source_name=source.name, source_fingerprint=digest, status="running", source_stats=stats)
    session.add(batch)
    session.flush()
    imported = {"accepted": 0, "rejected": 0, "duplicates": 0}
    reasons: Counter[str] = Counter()
    for group, records in (("accepted", accepted), ("rejected", rejected), ("duplicate", duplicates)):
        for index, item in enumerate(records):
            was_added, _post = _add_post(session, batch.id, item, group, index)
            key = "duplicates" if group == "duplicate" else group
            imported[key] += int(was_added)
            if group == "rejected":
                reasons[str(item.get("reason") or "غير محدد")] += 1
    _add_usage(session, batch.id, stats)
    total = sum(imported.values())
    job = ProcessingJob(
        name="استيراد {0}".format(source.name), status="completed", total_posts=total,
        completed_posts=imported["accepted"] + imported["duplicates"], failed_posts=imported["rejected"],
        started_at=batch.started_at, finished_at=datetime.now(timezone.utc),
        errors=[{"reason": key, "count": value} for key, value in reasons.items()], import_batch_id=batch.id,
    )
    session.add(job)
    batch.status = "completed"
    batch.accepted_count = imported["accepted"]
    batch.rejected_count = imported["rejected"]
    batch.duplicate_count = imported["duplicates"]
    batch.rejection_reasons = dict(reasons)
    batch.finished_at = datetime.now(timezone.utc)
    session.add(SystemEvent(event_type="legacy_import_completed", entity_type="import_batch", entity_id=batch.id,
                            details={"accepted": imported["accepted"], "rejected": imported["rejected"], "duplicates": imported["duplicates"]}))
    session.commit()
    return {"batch_id": batch.id, "status": batch.status, **imported, "rejection_reasons": dict(reasons)}
