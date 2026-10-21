"""Persistent processing job API and background orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai_tests import get_ai_provider_factory
from .database import SessionLocal, get_session
from .models import AIProviderConfig, ProcessingJob, ProcessingJobItem, SourcePost
from .processing.jobs import process_job_until_blocked, refresh_job_stats
from .providers.base import AIProvider

router = APIRouter(prefix="/api/processing", tags=["processing-center"])


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="معالجة عقارات محددة", min_length=1, max_length=200)
    post_ids: list[int] = Field(min_length=1, max_length=100)
    provider_key: Literal["kilo", "ollama", "openvino"] = "kilo"
    max_retries: int = Field(default=1, ge=0, le=5)
    max_requests: int | None = Field(default=None, ge=1, le=1000)
    max_tokens_budget: int | None = Field(default=None, ge=1)
    max_cost_budget: float | None = Field(default=None, ge=0)
    force_reprocess: bool = False
    confirmed_cloud_processing: bool = False

    @field_validator("post_ids")
    @classmethod
    def unique_posts(cls, value):
        if len(value) != len(set(value)): raise ValueError("لا يجوز تكرار المنشور داخل المهمة")
        if any(item <= 0 for item in value): raise ValueError("معرف المنشور غير صالح")
        return value


def _iso(value: datetime | None): return value.isoformat() if value else None


def _job_dict(session: Session, job: ProcessingJob):
    refresh_job_stats(session, job)
    items = session.scalars(select(ProcessingJobItem).where(ProcessingJobItem.job_id == job.id).order_by(ProcessingJobItem.position)).all()
    return {
        "id": job.id, "name": job.name, "status": job.status, "provider_config_id": job.provider_config_id,
        "total_posts": job.total_posts, "completed_posts": job.completed_posts, "failed_posts": job.failed_posts,
        "max_retries": job.max_retries, "max_requests": job.max_requests, "max_tokens_budget": job.max_tokens_budget,
        "max_cost_budget": job.max_cost_budget, "actual_requests": job.actual_requests,
        "input_tokens": job.input_tokens, "output_tokens": job.output_tokens, "total_tokens": job.total_tokens,
        "actual_cost": job.actual_cost, "average_response_time_ms": job.average_response_time_ms,
        "started_at": _iso(job.started_at), "finished_at": _iso(job.finished_at), "created_at": _iso(job.created_at),
        "errors": job.errors, "items": [{"id": item.id, "post_id": item.source_post_id, "status": item.status,
            "attempt_count": item.attempt_count, "ai_test_run_id": item.ai_test_run_id,
            "error_type": item.last_error_type, "error_message": item.last_error_message} for item in items],
    }


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, session: Session = Depends(get_session)):
    provider = session.scalar(select(AIProviderConfig).where(AIProviderConfig.provider_key == payload.provider_key))
    if not provider: raise HTTPException(404, "المزود غير موجود")
    if provider.operation_mode == "cloud" and not payload.confirmed_cloud_processing:
        raise HTTPException(422, "يلزم تأكيد صريح لمعالجة الدفعة عبر مزود سحابي")
    existing_posts = set(session.scalars(select(SourcePost.id).where(SourcePost.id.in_(payload.post_ids))).all())
    if existing_posts != set(payload.post_ids): raise HTTPException(404, "بعض المنشورات غير موجودة")
    if not payload.force_reprocess:
        duplicate = session.scalar(select(ProcessingJobItem.source_post_id).where(
            ProcessingJobItem.source_post_id.in_(payload.post_ids), ProcessingJobItem.status == "succeeded"
        ).limit(1))
        if duplicate: raise HTTPException(409, f"المنشور {duplicate} عولج بنجاح سابقاً؛ استخدم إعادة المعالجة الصريحة")
    job = ProcessingJob(
        name=payload.name, status="queued", total_posts=len(payload.post_ids), completed_posts=0, failed_posts=0,
        provider_config_id=provider.id, max_retries=payload.max_retries, max_requests=payload.max_requests,
        max_tokens_budget=payload.max_tokens_budget, max_cost_budget=payload.max_cost_budget,
        force_reprocess=payload.force_reprocess, actual_requests=0,
    )
    session.add(job); session.flush()
    for position, post_id in enumerate(payload.post_ids):
        session.add(ProcessingJobItem(job_id=job.id, source_post_id=post_id, position=position, status="queued"))
    session.commit(); session.refresh(job); return _job_dict(session, job)


@router.get("/jobs")
def list_jobs(session: Session = Depends(get_session)):
    jobs = session.scalars(select(ProcessingJob).order_by(ProcessingJob.id.desc())).all()
    return [_job_dict(session, job) for job in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(ProcessingJob, job_id)
    if not job: raise HTTPException(404, "المهمة غير موجودة")
    return _job_dict(session, job)


def _schedule(job: ProcessingJob, tasks: BackgroundTasks, factory):
    job.status = "queued"
    tasks.add_task(process_job_until_blocked, SessionLocal, job.id, factory)


@router.post("/jobs/{job_id}/start")
def start_job(job_id: int, tasks: BackgroundTasks, session: Session = Depends(get_session), factory=Depends(get_ai_provider_factory)):
    job = session.get(ProcessingJob, job_id)
    if not job: raise HTTPException(404, "المهمة غير موجودة")
    if job.status not in {"queued", "paused", "limit_reached"}: raise HTTPException(409, "حالة المهمة لا تسمح بالتشغيل")
    _schedule(job, tasks, factory); session.commit(); return {"status": "queued", "job_id": job.id}


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(ProcessingJob, job_id)
    if not job: raise HTTPException(404, "المهمة غير موجودة")
    if job.status not in {"running", "queued"}: raise HTTPException(409, "المهمة غير نشطة")
    job.status = "pause_requested" if job.status == "running" else "paused"; session.commit(); return {"status": job.status}


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: int, tasks: BackgroundTasks, session: Session = Depends(get_session), factory=Depends(get_ai_provider_factory)):
    job = session.get(ProcessingJob, job_id)
    if not job: raise HTTPException(404, "المهمة غير موجودة")
    if job.status not in {"paused", "limit_reached"}: raise HTTPException(409, "المهمة ليست متوقفة")
    _schedule(job, tasks, factory); session.commit(); return {"status": "queued"}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(ProcessingJob, job_id)
    if not job: raise HTTPException(404, "المهمة غير موجودة")
    job.status = "cancel_requested" if job.status == "running" else "canceled"
    if job.status == "canceled":
        for item in job.items:
            if item.status == "queued": item.status = "canceled"
    session.commit(); return {"status": job.status}


@router.post("/jobs/{job_id}/retry-failed")
def retry_failed(job_id: int, tasks: BackgroundTasks, session: Session = Depends(get_session), factory=Depends(get_ai_provider_factory)):
    job = session.get(ProcessingJob, job_id)
    if not job: raise HTTPException(404, "المهمة غير موجودة")
    changed = 0
    for item in job.items:
        if item.status == "failed" and item.attempt_count < 1 + job.max_retries:
            item.status = "queued"; item.finished_at = None; changed += 1
    if not changed: raise HTTPException(409, "لا توجد عناصر فاشلة مؤهلة لإعادة المحاولة")
    job.finished_at = None; _schedule(job, tasks, factory); session.commit(); return {"status": "queued", "retry_items": changed}
