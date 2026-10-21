"""Small provider contract that is fully replaceable in automated tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderRequest:
    model: str
    messages: list[dict[str, str]]
    max_tokens: int | None
    timeout_seconds: int


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    requested_model: str
    actual_model: str | None
    http_status: int
    finish_reason: str | None
    duration_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    actual_cost: float | None = None
    cost_currency: str | None = None
    raw_body: str | None = None


class ProviderFailure(RuntimeError):
    def __init__(self, kind: str, message: str, *, http_status: int | None = None,
                 duration_ms: float | None = None, raw_body: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.duration_ms = duration_ms
        self.raw_body = raw_body


class AIProvider(Protocol):
    def complete(self, request: ProviderRequest) -> ProviderResponse: ...
