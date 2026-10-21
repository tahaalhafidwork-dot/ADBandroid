"""Validated API request models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

