"""One-shot, non-streaming Kilo AI Gateway adapter with no retry behavior."""

from __future__ import annotations

import json
import time
from urllib.parse import urlparse

import httpx

from .base import ProviderFailure, ProviderRequest, ProviderResponse

ALLOWED_HOSTS = {"api.kilo.ai", "ai-gateway.kilo.ai"}
MAX_RAW_RESPONSE = 32_768


def validate_kilo_base_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Kilo API must use an approved official HTTPS host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Kilo API URL must not contain credentials, query, or fragment")
    path = parsed.path.rstrip("/")
    if path not in {"/api/gateway", "/api/v1"}:
        raise ValueError("Kilo API base path is not an approved gateway path")
    return value.rstrip("/")


class KiloProvider:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = validate_kilo_base_url(base_url)
        if not api_key.strip():
            raise ValueError("KILO_API_KEY is required")
        self._api_key = api_key

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        payload: dict[str, object] = {
            "model": request.model,
            "messages": request.messages,
            "stream": False,
            "temperature": 0,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        start = time.perf_counter()
        try:
            # A fresh client plus one post means transport retries are impossible.
            with httpx.Client(timeout=request.timeout_seconds, follow_redirects=False) as client:
                response = client.post(
                    self.base_url + "/chat/completions",
                    headers={"Authorization": "Bearer " + self._api_key, "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            elapsed = (time.perf_counter() - start) * 1000
            raise ProviderFailure("timeout", "Kilo request timed out", duration_ms=elapsed) from exc
        except httpx.HTTPError as exc:
            elapsed = (time.perf_counter() - start) * 1000
            raise ProviderFailure("connection_error", "Kilo connection failed", duration_ms=elapsed) from exc
        elapsed = (time.perf_counter() - start) * 1000
        raw = response.text[:MAX_RAW_RESPONSE]
        if response.status_code != 200:
            raise ProviderFailure(
                "http_error", "Kilo returned HTTP {0}".format(response.status_code),
                http_status=response.status_code, duration_ms=elapsed, raw_body=raw,
            )
        try:
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message content is not text")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderFailure(
                "invalid_provider_response", "Kilo response did not match chat completions format",
                http_status=200, duration_ms=elapsed, raw_body=raw,
            ) from exc
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
        total_tokens = usage.get("total_tokens")
        microdollars = usage.get("cost_microdollars")
        try:
            actual_cost = float(microdollars) / 1_000_000 if microdollars is not None and not isinstance(microdollars, bool) else None
        except (TypeError, ValueError):
            actual_cost = None
        return ProviderResponse(
            content=content, requested_model=request.model,
            actual_model=body.get("model") if isinstance(body.get("model"), str) else None,
            http_status=200, finish_reason=choice.get("finish_reason"), duration_ms=elapsed,
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            total_tokens=total_tokens if isinstance(total_tokens, int) else None,
            actual_cost=actual_cost, cost_currency="USD" if actual_cost is not None else None,
            raw_body=json.dumps(body, ensure_ascii=False)[:MAX_RAW_RESPONSE],
        )
