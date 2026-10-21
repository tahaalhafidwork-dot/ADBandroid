"""Validated API request models."""

from __future__ import annotations

from typing import Literal

from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ReviewStatus = Literal["draft", "needs_review", "approved", "rejected"]
ApprovalStatus = Literal["draft", "approved", "rejected"]


class ListingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_type: str | None = Field(default=None, max_length=50)
    property_type: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=20)
    area_sqm: float | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: int | None = Field(default=None, ge=0, le=100)
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=160)
    complex_name: str | None = Field(default=None, max_length=160)
    floor: str | None = Field(default=None, max_length=80)
    furnished: bool | None = None
    verification_status: str | None = Field(default=None, max_length=40)
    review_status: ReviewStatus | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value


class DialectTermCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str = Field(min_length=1, max_length=120)
    meaning: str = Field(min_length=1, max_length=2000)
    context: str | None = Field(default=None, max_length=2000)
    usage_example: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    approval_status: ApprovalStatus = "draft"

    @field_validator("term", "meaning")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("القيمة مطلوبة")
        return value


class DialectTermPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str | None = Field(default=None, min_length=1, max_length=120)
    meaning: str | None = Field(default=None, min_length=1, max_length=2000)
    context: str | None = Field(default=None, max_length=2000)
    usage_example: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    approval_status: ApprovalStatus | None = None


class LegacyImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(default="aqarati_50_results.json", max_length=250)


class ProviderSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=100)
    api_base_url: str = Field(min_length=1, max_length=500)
    model_name: str | None = Field(default=None, max_length=200)
    is_enabled: bool = False
    operation_mode: Literal["cloud", "local"]
    max_tokens: int | None = Field(default=None, ge=1, le=2_000_000)
    timeout_seconds: int = Field(default=30, ge=1, le=3600)
    request_limit: int | None = Field(default=None, ge=1, le=1_000_000)
    cost_cap: float | None = Field(default=None, ge=0, le=1_000_000)

    @field_validator("api_base_url")
    @classmethod
    def validate_api_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("عنوان API يجب أن يستخدم http أو https")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("عنوان API لا يجوز أن يحتوي بيانات اعتماد أو query أو fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_safe_mode(self):
        hostname = (urlparse(self.api_base_url).hostname or "").lower()
        if self.operation_mode == "local" and hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("المزود المحلي يجب أن يستخدم عنوان loopback")
        if self.is_enabled and not (self.model_name and self.model_name.strip()):
            raise ValueError("اسم النموذج مطلوب قبل التفعيل")
        return self


class ProviderSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, max_length=200)
    is_enabled: bool | None = None
    operation_mode: Literal["cloud", "local"] | None = None
    max_tokens: int | None = Field(default=None, ge=1, le=2_000_000)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    request_limit: int | None = Field(default=None, ge=1, le=1_000_000)
    cost_cap: float | None = Field(default=None, ge=0, le=1_000_000)

    @field_validator("api_base_url")
    @classmethod
    def validate_optional_api_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return ProviderSettings.validate_api_url(value)
