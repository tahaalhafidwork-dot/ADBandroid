"""OCR selection, extraction, correction, and review endpoints."""

from __future__ import annotations

import shutil
import time
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .database import get_session
from .models import ListingDraft, OCRResult, SourcePost
from .ocr import OCREngine, OCRFailure, TesseractEngine, download_image, extract_suggestions, image_type, read_local_image
from . import paths

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


class OCRRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_id: int = Field(gt=0)
    image_index: int | None = Field(default=None, ge=0)
    local_path: str | None = Field(default=None, max_length=500)
    languages: str = Field(default="ara+kur+eng", pattern=r"^[a-z]{3}(?:\+[a-z]{3}){0,4}$")

    @model_validator(mode="after")
    def one_source(self):
        if (self.image_index is None) == (self.local_path is None): raise ValueError("اختر صورة منشور أو ملفاً محلياً واحداً")
        return self


class OCRCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    corrected_text: str = Field(max_length=20000)


class OCRReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(pattern="^(approve|reject)$")


def get_ocr_engine() -> OCREngine:
    try:
        return TesseractEngine()
    except OCRFailure as exc:
        failure_kind, failure_message = exc.kind, str(exc)

        class UnavailableOCREngine:
            name = "unavailable"

            def extract(self, _data: bytes, _languages: str) -> str:
                raise OCRFailure(failure_kind, failure_message)

        return UnavailableOCREngine()


def _dict(row: OCRResult):
    return {"id": row.id, "post_id": row.source_post_id, "image_index": row.image_index,
            "source_kind": row.source_kind, "source_reference": row.source_reference,
            "image_url": f"/api/ocr/{row.id}/image" if row.cached_image_path else None, "engine": row.engine,
            "languages": row.languages, "status": row.status, "extracted_text": row.extracted_text,
            "corrected_text": row.corrected_text, "suggestions": row.structured_suggestions,
            "review_status": row.review_status, "error_type": row.error_type, "error_message": row.error_message,
            "duration_ms": row.duration_ms, "created_at": row.created_at.isoformat()}


@router.get("/capabilities")
def capabilities():
    return {"optional": True, "tesseract_installed": bool(shutil.which("tesseract")),
            "languages_requested": ["ara", "kur", "eng"], "paid_service_used": False}


@router.post("/extract", status_code=status.HTTP_201_CREATED)
def extract(payload: OCRRequest, session: Session = Depends(get_session), engine: OCREngine = Depends(get_ocr_engine)):
    post = session.get(SourcePost, payload.post_id)
    if not post: raise HTTPException(404, "المنشور غير موجود")
    source_kind = "local" if payload.local_path else "remote"
    reference = payload.local_path or ""
    started = time.perf_counter()
    cached_image_path = None
    try:
        if payload.local_path:
            data = read_local_image(payload.local_path)
        else:
            urls = post.image_urls or []
            if payload.image_index >= len(urls): raise OCRFailure("image_not_found", "صورة المنشور غير موجودة")
            reference = urls[payload.image_index]
            if not Settings.load().enable_image_download: raise OCRFailure("download_disabled", "تنزيل الصور الخارجية معطل")
            data = download_image(reference)
        extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[image_type(data)]
        cached_image_path = f"processed/ocr-images/{sha256(data).hexdigest()}{extension}"
        paths.write_bytes(paths.data_path(*cached_image_path.split("/")), data)
        text = engine.extract(data, payload.languages)
        row = OCRResult(source_post_id=post.id, image_index=payload.image_index, source_kind=source_kind,
            source_reference=reference, cached_image_path=cached_image_path, engine=engine.name, languages=payload.languages, status="succeeded",
            extracted_text=text, structured_suggestions=extract_suggestions(text), duration_ms=(time.perf_counter()-started)*1000)
    except OCRFailure as exc:
        row = OCRResult(source_post_id=post.id, image_index=payload.image_index, source_kind=source_kind,
            source_reference=reference, cached_image_path=cached_image_path, engine=getattr(engine, "name", "unavailable"), languages=payload.languages,
            status="failed", error_type=exc.kind, error_message=str(exc), duration_ms=(time.perf_counter()-started)*1000)
    session.add(row); session.commit(); session.refresh(row); return _dict(row)


@router.get("/{result_id}/image", response_class=FileResponse)
def result_image(result_id: int, session: Session = Depends(get_session)):
    row = session.get(OCRResult, result_id)
    if not row or not row.cached_image_path: raise HTTPException(404, "لا توجد نسخة محلية للصورة")
    candidate = paths.ensure_inside_project(paths.data_path(*row.cached_image_path.split("/")))
    if not paths.is_inside(candidate, paths.data_path()) or not candidate.is_file():
        raise HTTPException(404, "ملف الصورة غير موجود")
    return FileResponse(candidate, media_type=image_type(candidate.read_bytes()))


@router.get("")
def list_results(post_id: int | None = Query(default=None, gt=0), session: Session = Depends(get_session)):
    statement = select(OCRResult).order_by(OCRResult.id.desc())
    if post_id: statement = statement.where(OCRResult.source_post_id == post_id)
    return [_dict(row) for row in session.scalars(statement).all()]


@router.patch("/{result_id}")
def correct(result_id: int, payload: OCRCorrection, session: Session = Depends(get_session)):
    row = session.get(OCRResult, result_id)
    if not row: raise HTTPException(404, "نتيجة OCR غير موجودة")
    row.corrected_text = payload.corrected_text.strip(); row.structured_suggestions = extract_suggestions(row.corrected_text)
    row.review_status = "corrected"; session.commit(); session.refresh(row); return _dict(row)


@router.post("/{result_id}/review")
def review(result_id: int, payload: OCRReview, session: Session = Depends(get_session)):
    row = session.get(OCRResult, result_id)
    if not row: raise HTTPException(404, "نتيجة OCR غير موجودة")
    row.review_status = "approved" if payload.action == "approve" else "rejected"
    listing = session.scalar(select(ListingDraft).where(ListingDraft.source_post_id == row.source_post_id))
    conflicts = {}
    if listing and row.structured_suggestions:
        for key, value in row.structured_suggestions.items():
            existing = getattr(listing, key, None)
            if existing is not None and existing != value: conflicts[key] = {"existing": existing, "suggested": value}
    session.commit()
    return {"result": _dict(row), "merge_proposal": row.structured_suggestions or {}, "conflicts": conflicts,
            "listing_modified": False, "message": "المقترحات تحتاج تطبيقاً يدوياً ولا تستبدل القيم المؤكدة"}
