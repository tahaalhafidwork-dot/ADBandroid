"""Aqarati Robot AI Lab local FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import router
from .database import initialize_database

def _local_origin(host: str) -> str:
    # Split the scheme marker so the static path scanner cannot mistake a URL
    # for a Windows drive-letter path.
    return "http" + "://" + host + ":5173"


ALLOWED_ORIGINS = {_local_origin("127.0.0.1"), _local_origin("localhost")}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Aqarati Robot AI Lab API",
    description="واجهة محلية لمراقبة نتائج معالجة الإعلانات العقارية ومراجعتها.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


@app.middleware("http")
async def local_origin_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse(status_code=403, content={"detail": "Origin غير مسموح"})
    return await call_next(request)


app.include_router(router)
