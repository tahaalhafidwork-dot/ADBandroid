"""Strict structured output contract for the real-estate extraction experiment."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

Category = Literal["for_sale", "for_rent", "real_estate_service", "unclear", "not_real_estate"]
PropertyType = Literal[
    "apartment", "house", "land", "villa", "commercial", "office", "building",
    "farm", "warehouse", "room", "other", "unclear",
]


class ExtractionResult(BaseModel):
    """Every field is required in JSON; legitimately unknown values may be null."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    property_type: PropertyType | None
    title: str | None = Field(max_length=500)
    description: str | None = Field(max_length=5000)
    price: float | None = Field(ge=0)
    currency: Literal["IQD", "USD"] | None
    area_sqm: float | None = Field(ge=0)
    bedrooms: int | None = Field(ge=0, le=100)
    bathrooms: int | None = Field(ge=0, le=100)
    city: str | None = Field(max_length=100)
    district: str | None = Field(max_length=160)
    complex_name: str | None = Field(max_length=160)
    floor: str | None = Field(max_length=80)
    furnished: bool | None
    confidence: float = Field(ge=0, le=1)
    uncertain_fields: list[str] = Field(max_length=30)
    needs_review: bool
    review_notes: list[str] = Field(max_length=20)

    @field_validator("title", "description", "city", "district", "complex_name", "floor")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("uncertain_fields", "review_notes")
    @classmethod
    def clean_lists(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class OutputParseError(ValueError):
    def __init__(self, kind: str, message: str, *, truncated: bool = False):
        super().__init__(message)
        self.kind = kind
        self.truncated = truncated


_FENCE = re.compile(r"^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$", re.IGNORECASE)


def parse_extraction_output(content: str, finish_reason: str | None) -> ExtractionResult:
    """Strip one complete code fence, parse once, and never repair model output."""
    candidate = content.strip()
    fence = _FENCE.fullmatch(candidate)
    if fence:
        candidate = fence.group(1).strip()
    is_truncated = finish_reason in {"length", "max_tokens"}
    try:
        decoded = json.loads(candidate)
    except json.JSONDecodeError as exc:
        looks_cut = is_truncated or (
            candidate.startswith(("{", "[")) and not candidate.endswith(("}", "]"))
        )
        raise OutputParseError("truncated_json" if looks_cut else "invalid_json", str(exc), truncated=looks_cut) from exc
    if not isinstance(decoded, dict):
        raise OutputParseError("invalid_schema", "root JSON value must be an object")
    try:
        return ExtractionResult.model_validate(decoded)
    except ValidationError as exc:
        raise OutputParseError("invalid_schema", str(exc)) from exc
