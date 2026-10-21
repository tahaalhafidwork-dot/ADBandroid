"""Aqarati draft integration control plane."""

from __future__ import annotations

import os
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .config import Settings
from .database import get_session
from .integrations.aqarati import AqaratiConnector, AqaratiFailure, HttpAqaratiConnector, validate_base_url
from .models import AqaratiIntegrationConfig, AqaratiSyncRecord, ListingDraft, SourcePost

router = APIRouter(prefix="/api/aqarati", tags=["aqarati-integration"])


class IntegrationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str | None = Field(default=None, max_length=500)
    service_identity: str | None = Field(default=None, min_length=1, max_length=100)
    draft_path: str | None = Field(default=None, pattern=r"^/[A-Za-z0-9/_-]+$", max_length=250)
    is_enabled: bool | None = None

    @field_validator("base_url")
    @classmethod
    def safe_url(cls, value): return validate_base_url(value) if value else value


class ConnectionTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed_external_connection: bool


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    listing_id: int = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    confirmed_draft_sync: bool
    include_images: bool = False
    confirmed_image_rights: bool = False


def get_aqarati_connector_factory() -> Callable[[AqaratiIntegrationConfig, str], AqaratiConnector]:
    return lambda config, token: HttpAqaratiConnector(config.base_url or "", config.draft_path, config.service_identity, token)


def _config(session: Session):
    row = session.get(AqaratiIntegrationConfig, 1)
    if not row:
        row = AqaratiIntegrationConfig(id=1, service_identity="Aqarati Robot", draft_path="/api/robot/drafts", is_enabled=False)
        session.add(row); session.commit(); session.refresh(row)
    return row


def _config_dict(row):
    return {"id": row.id, "base_url": row.base_url, "service_identity": row.service_identity,
            "draft_path": row.draft_path, "is_enabled": row.is_enabled, "connection_status": row.connection_status,
            "last_error": row.last_error, "credential_present": bool(os.environ.get("AQARATI_SERVICE_TOKEN", "")),
            "runtime_switch": Settings.load().enable_aqarati_sync}


def _payload(listing: ListingDraft, include_images: bool):
    post = listing.source_post
    return {
        "lifecycle": "draft", "publish": False, "source": "Aqarati Robot", "local_listing_id": listing.id,
        "listing": {key: getattr(listing, key) for key in (
            "listing_type", "property_type", "title", "description", "price", "currency", "area_sqm",
            "bedrooms", "bathrooms", "city", "district", "complex_name", "floor", "furnished", "confidence",
        )},
        "images": list(post.image_urls or []) if include_images else [],
        "source_reference": post.source_identifier,
    }


def _record_dict(row):
    return {"id": row.id, "listing_id": row.listing_id, "status": row.status,
            "remote_draft_id": row.remote_draft_id, "attempt_count": row.attempt_count,
            "include_images": row.include_images, "http_status": row.http_status,
            "error_type": row.error_type, "error_message": row.error_message,
            "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


@router.get("/config")
def get_config(session: Session = Depends(get_session)): return _config_dict(_config(session))


@router.patch("/config")
def update_config(payload: IntegrationPatch, session: Session = Depends(get_session)):
    row = _config(session)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    if row.is_enabled and not row.base_url: raise HTTPException(422, "عنوان Aqarati مطلوب قبل التفعيل")
    row.connection_status = "not_tested"; row.last_error = None; session.commit(); session.refresh(row); return _config_dict(row)


@router.post("/connection-test")
def test_connection(payload: ConnectionTest, session: Session = Depends(get_session), factory=Depends(get_aqarati_connector_factory)):
    row = _config(session); settings = Settings.load(); token = os.environ.get("AQARATI_SERVICE_TOKEN", "")
    if not payload.confirmed_external_connection or not settings.enable_aqarati_sync or not row.is_enabled or not token:
        raise HTTPException(409, "اختبار الاتصال الخارجي غير مفعل أو غير مؤكد أو بيانات الاعتماد مفقودة")
    try:
        capabilities = factory(row, token).capabilities(); row.connection_status = "connected"; row.last_error = None
        session.commit(); return {"status": "connected", "capabilities": capabilities}
    except AqaratiFailure as exc:
        row.connection_status = "failed"; row.last_error = str(exc); session.commit(); raise HTTPException(502, str(exc)) from exc


@router.get("/draft-preview/{listing_id}")
def draft_preview(listing_id: int, include_images: bool = False, session: Session = Depends(get_session)):
    listing = session.scalar(select(ListingDraft).where(ListingDraft.id == listing_id).options(joinedload(ListingDraft.source_post)))
    if not listing: raise HTTPException(404, "المسودة المحلية غير موجودة")
    if listing.review_status != "approved": raise HTTPException(409, "لا يمكن إرسال عقار غير معتمد محلياً")
    return {"payload": _payload(listing, include_images), "will_publish": False, "requires_confirmation": True}


@router.post("/sync", status_code=status.HTTP_201_CREATED)
def sync(payload: SyncRequest, session: Session = Depends(get_session), factory=Depends(get_aqarati_connector_factory)):
    existing = session.scalar(select(AqaratiSyncRecord).where(AqaratiSyncRecord.idempotency_key == payload.idempotency_key))
    if existing:
        if existing.listing_id != payload.listing_id: raise HTTPException(409, "مفتاح منع التكرار مستخدم لمسودة أخرى")
        return _record_dict(existing)
    listing = session.scalar(select(ListingDraft).where(ListingDraft.id == payload.listing_id).options(joinedload(ListingDraft.source_post)))
    if not listing: raise HTTPException(404, "المسودة المحلية غير موجودة")
    if listing.review_status != "approved": raise HTTPException(409, "المسودة غير معتمدة")
    if not payload.confirmed_draft_sync: raise HTTPException(422, "يلزم تأكيد إرسال المسودة")
    if payload.include_images and not payload.confirmed_image_rights: raise HTTPException(422, "يلزم تأكيد حق استخدام الصور")
    config = _config(session); token = os.environ.get("AQARATI_SERVICE_TOKEN", "")
    if not (Settings.load().enable_aqarati_sync and config.is_enabled and config.base_url and token):
        raise HTTPException(409, "تكامل Aqarati الفعلي معطل أو غير مكتمل")
    body = _payload(listing, payload.include_images)
    record = AqaratiSyncRecord(listing_id=listing.id, idempotency_key=payload.idempotency_key,
        status="sending", attempt_count=1, include_images=payload.include_images, payload_snapshot=body)
    session.add(record); session.commit(); session.refresh(record)
    try:
        result = factory(config, token).create_draft(body, payload.idempotency_key)
        record.status = "draft_created"; record.remote_draft_id = result.remote_draft_id; record.http_status = result.http_status
    except AqaratiFailure as exc:
        record.status = "failed"; record.error_type = exc.kind; record.error_message = str(exc); record.http_status = exc.http_status
    session.commit(); session.refresh(record); return _record_dict(record)


@router.get("/sync")
def sync_records(session: Session = Depends(get_session)):
    return [_record_dict(row) for row in session.scalars(select(AqaratiSyncRecord).order_by(AqaratiSyncRecord.id.desc())).all()]


@router.post("/sync/{record_id}/retry")
def retry_sync(record_id: int, session: Session = Depends(get_session), factory=Depends(get_aqarati_connector_factory)):
    record = session.get(AqaratiSyncRecord, record_id)
    if not record or record.status != "failed": raise HTTPException(409, "السجل غير مؤهل لإعادة المحاولة")
    config = _config(session); token = os.environ.get("AQARATI_SERVICE_TOKEN", "")
    if not (Settings.load().enable_aqarati_sync and config.is_enabled and token): raise HTTPException(409, "التكامل معطل")
    record.attempt_count += 1
    try:
        result = factory(config, token).create_draft(record.payload_snapshot, record.idempotency_key)
        record.status = "draft_created"; record.remote_draft_id = result.remote_draft_id; record.http_status = result.http_status
        record.error_type = None; record.error_message = None
    except AqaratiFailure as exc:
        record.error_type = exc.kind; record.error_message = str(exc); record.http_status = exc.http_status
    session.commit(); session.refresh(record); return _record_dict(record)
