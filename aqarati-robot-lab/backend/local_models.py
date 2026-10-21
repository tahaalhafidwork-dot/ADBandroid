"""Explicit local-only discovery endpoints; they never start or download models."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_session
from .models import AIProviderConfig
from .providers.base import ProviderFailure
from .providers.local import discover_local_models

router = APIRouter(prefix="/api/local-models", tags=["local-models"])


@router.get("/{provider_key}/discover")
def discover(provider_key: str, session: Session = Depends(get_session)):
    if provider_key not in {"ollama", "openvino"}:
        raise HTTPException(404, "المزود المحلي غير مدعوم")
    provider = session.query(AIProviderConfig).filter_by(provider_key=provider_key).one_or_none()
    if not provider:
        raise HTTPException(404, "إعداد المزود غير موجود")
    try:
        models = discover_local_models(provider.api_base_url, provider_key, provider.timeout_seconds)
        provider.connection_status = "connected"
        session.commit()
        return {"provider_key": provider_key, "models": models, "installed": True, "started_by_lab": False}
    except ProviderFailure as exc:
        provider.connection_status = "failed"; session.commit()
        return {"provider_key": provider_key, "models": [], "installed": False, "started_by_lab": False, "error": str(exc)}
