"""Loopback-only OpenAI-compatible adapters for optional local model servers."""

from __future__ import annotations

import json
import time
from urllib.parse import urlparse

import httpx

from .base import ProviderFailure, ProviderRequest, ProviderResponse

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_BODY = 32_768


def validate_local_base_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError("local model URL must use a loopback host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("local model URL must not include credentials, query, or fragment")
    return value.rstrip("/")


class LocalOpenAIProvider:
    def __init__(self, base_url: str, provider_key: str):
        self.base_url = validate_local_base_url(base_url)
        self.provider_key = provider_key

    @property
    def chat_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return self.base_url + "/chat/completions"
        return self.base_url + "/v1/chat/completions"

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        payload: dict[str, object] = {
            "model": request.model, "messages": request.messages,
            "stream": False, "temperature": 0,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=request.timeout_seconds, follow_redirects=False, trust_env=False) as client:
                response = client.post(self.chat_url, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout", "local model request timed out", duration_ms=(time.perf_counter()-started)*1000) from exc
        except httpx.HTTPError as exc:
            raise ProviderFailure("connection_error", "local model connection failed", duration_ms=(time.perf_counter()-started)*1000) from exc
        elapsed = (time.perf_counter()-started)*1000
        raw = response.text[:MAX_BODY]
        if response.status_code != 200:
            raise ProviderFailure("http_error", f"local model returned HTTP {response.status_code}", http_status=response.status_code, duration_ms=elapsed, raw_body=raw)
        try:
            body = response.json(); choice = body["choices"][0]; content = choice["message"]["content"]
            if not isinstance(content, str): raise TypeError
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderFailure("invalid_provider_response", "local response is not OpenAI-compatible", http_status=200, duration_ms=elapsed, raw_body=raw) from exc
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        def token(*names: str) -> int | None:
            for name in names:
                value = usage.get(name)
                if isinstance(value, int): return value
            return None
        return ProviderResponse(
            content=content, requested_model=request.model,
            actual_model=body.get("model") if isinstance(body.get("model"), str) else None,
            http_status=200, finish_reason=choice.get("finish_reason"), duration_ms=elapsed,
            input_tokens=token("prompt_tokens", "input_tokens"),
            output_tokens=token("completion_tokens", "output_tokens"), total_tokens=token("total_tokens"),
            raw_body=json.dumps(body, ensure_ascii=False)[:MAX_BODY],
        )


def discover_local_models(base_url: str, provider_key: str, timeout_seconds: int = 3) -> list[str]:
    base = validate_local_base_url(base_url)
    url = base + "/api/tags" if provider_key == "ollama" else (base + "/models" if base.endswith("/v1") else base + "/v1/models")
    try:
        with httpx.Client(timeout=min(timeout_seconds, 5), follow_redirects=False, trust_env=False) as client:
            response = client.get(url)
        response.raise_for_status(); body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderFailure("connection_error", "local model discovery failed") from exc
    if provider_key == "ollama":
        models = body.get("models", []) if isinstance(body, dict) else []
        return sorted({str(row.get("name")) for row in models if isinstance(row, dict) and row.get("name")})
    rows = body.get("data", []) if isinstance(body, dict) else []
    return sorted({str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id")})
