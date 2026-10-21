"""Persistent, step-wise processing queue built on the single-post experiment engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai_tests import _load_subject, run_test
from ..models import AIProviderConfig, AITestRun, ProcessingJob, ProcessingJobItem
from ..providers.base import AIProvider
from ..schemas import AITestRunRequest

TERMINAL_ITEM_STATES = {"succeeded", "failed", "canceled", "skipped"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def recover_interrupted_jobs(session: Session) -> int:
    items = session.scalars(select(ProcessingJobItem).where(ProcessingJobItem.status == "running")).all()
    for item in items:
        item.status = "queued"; item.started_at = None
    jobs = session.scalars(select(ProcessingJob).where(
        ProcessingJob.provider_config_id.is_not(None),
        ProcessingJob.status.in_(["running", "pause_requested"]),
    )).all()
    for job in jobs:
        job.status = "paused" if job.status == "pause_requested" else "queued"
        job.updated_at = utcnow()
    canceled = session.scalars(select(ProcessingJob).where(
        ProcessingJob.provider_config_id.is_not(None), ProcessingJob.status == "cancel_requested",
    )).all()
    for job in canceled:
        job.status = "canceled"; job.finished_at = utcnow()
        for item in job.items:
            if item.status not in TERMINAL_ITEM_STATES:
                item.status = "canceled"; item.finished_at = utcnow()
    session.commit()
    return len(items)


def refresh_job_stats(session: Session, job: ProcessingJob) -> None:
    # Historical import jobs have no provider. Their original counters remain
    # authoritative and must never be replaced with AI queue item counts.
    if job.provider_config_id is None:
        return
    items = session.scalars(select(ProcessingJobItem).where(ProcessingJobItem.job_id == job.id)).all()
    job.completed_posts = sum(item.status == "succeeded" for item in items)
    job.failed_posts = sum(item.status == "failed" for item in items)
    run_ids = [item.ai_test_run_id for item in items if item.ai_test_run_id]
    runs = session.scalars(select(AITestRun).where(AITestRun.id.in_(run_ids))).all() if run_ids else []
    job.actual_requests = len(runs)

    def sum_known(name: str):
        if not runs or any(getattr(run, name) is None for run in runs): return None
        return sum(getattr(run, name) for run in runs)

    job.input_tokens = sum_known("input_tokens")
    job.output_tokens = sum_known("output_tokens")
    job.total_tokens = sum_known("total_tokens")
    job.actual_cost = sum_known("actual_cost")
    durations = [run.duration_ms for run in runs if run.duration_ms is not None]
    job.average_response_time_ms = sum(durations) / len(durations) if len(durations) == len(runs) and runs else None
    job.updated_at = utcnow()


def _limit_reason(job: ProcessingJob) -> str | None:
    if job.max_requests is not None and job.actual_requests >= job.max_requests: return "request_limit"
    if job.max_tokens_budget is not None:
        if job.actual_requests and job.total_tokens is None: return "token_usage_unavailable"
        if (job.total_tokens or 0) > job.max_tokens_budget: return "token_limit"
    if job.max_cost_budget is not None:
        if job.actual_requests and job.actual_cost is None: return "cost_usage_unavailable"
        if (job.actual_cost or 0) > job.max_cost_budget: return "cost_limit"
    return None


def process_job_step(session: Session, job_id: int, factory: Callable[[AIProviderConfig, str], AIProvider]) -> str:
    """Process at most one queued item and commit its outcome immediately."""
    job = session.get(ProcessingJob, job_id)
    if not job: raise KeyError(job_id)
    if job.status in {"paused", "pause_requested", "canceled", "cancel_requested", "completed"}: return job.status
    refresh_job_stats(session, job)
    reason = _limit_reason(job)
    if reason:
        job.status = "limit_reached"; job.errors = [{"reason": reason, "count": 1}]; session.commit(); return job.status
    item = session.scalar(select(ProcessingJobItem).where(
        ProcessingJobItem.job_id == job.id, ProcessingJobItem.status == "queued"
    ).order_by(ProcessingJobItem.position).limit(1))
    if item is None:
        pending = session.scalar(select(func.count(ProcessingJobItem.id)).where(
            ProcessingJobItem.job_id == job.id, ProcessingJobItem.status.not_in(TERMINAL_ITEM_STATES)
        )) or 0
        job.status = "completed" if pending == 0 else "paused"
        job.finished_at = utcnow() if pending == 0 else None
        refresh_job_stats(session, job); session.commit(); return job.status

    job.status = "running"; job.started_at = job.started_at or utcnow()
    item.status = "running"; item.attempt_count += 1; item.started_at = utcnow(); session.commit()
    provider = session.get(AIProviderConfig, job.provider_config_id)
    try:
        _post, _provider, _redacted, _messages, _snapshot, extra = _load_subject(session, item.source_post_id, provider.provider_key)
        request = AITestRunRequest(
            post_id=item.source_post_id, provider_key=provider.provider_key,
            preview_fingerprint=extra["fingerprint"],
            idempotency_key=f"job-{job.id}-item-{item.id}-attempt-{item.attempt_count}",
            confirmed_external_send=True, accepted_data_handling=True, accepted_unknown_cost=True,
        )
        result = run_test(request, session=session, factory=factory)
        item.ai_test_run_id = result["id"]
        item.status = "succeeded" if result["status"] == "succeeded" else "failed"
        item.last_error_type = result.get("failure_type"); item.last_error_message = result.get("failure_message")
    except HTTPException as exc:
        item.status = "failed"; item.last_error_type = "guard_blocked"; item.last_error_message = str(exc.detail)
    except Exception:
        item.status = "failed"; item.last_error_type = "internal_error"; item.last_error_message = "تعذر إكمال عنصر الطابور"
    item.finished_at = utcnow(); session.flush(); refresh_job_stats(session, job)
    session.refresh(job, attribute_names=["status"])
    if job.status == "cancel_requested":
        for pending_item in job.items:
            if pending_item.status == "queued":
                pending_item.status = "canceled"; pending_item.finished_at = utcnow()
        job.status = "canceled"; job.finished_at = utcnow(); session.commit(); return item.status
    if job.status == "pause_requested":
        job.status = "paused"; session.commit(); return item.status
    remaining = session.scalar(select(func.count(ProcessingJobItem.id)).where(
        ProcessingJobItem.job_id == job.id, ProcessingJobItem.status == "queued"
    )) or 0
    reason = _limit_reason(job)
    if reason and remaining:
        job.status = "limit_reached"; job.errors = [{"reason": reason, "count": 1}]
    elif not remaining:
        job.status = "completed"; job.finished_at = utcnow()
    session.commit()
    return item.status


def process_job_until_blocked(session_factory, job_id: int, factory) -> None:
    while True:
        with session_factory() as session:
            status = process_job_step(session, job_id, factory)
            job = session.get(ProcessingJob, job_id)
            if job.status != "running" or status not in {"succeeded", "failed"}: return
