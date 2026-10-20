"""Kilo AI Gateway model provider with prompt engineering improvements.

Calls the Kilo AI Gateway cloud API at https://api.kilo.ai/api/gateway
using the KILO_API_KEY environment variable for authentication.

Supports two extraction approaches:
- Method A: Classify then extract (two separate API calls)
- Method B: Single call for both classification and extraction

Features:
- Arabic prompts with JSON Schema and few-shot examples
- finish_reason tracking for truncated responses
- Single JSON repair attempt on parse failure
- PII stripping (phones, user IDs) before sending to model
- Cost and token tracking
- No credentials logged or transmitted to stdout
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from prompts import (
    get_classify_prompt,
    get_combined_prompt,
    get_extract_prompt,
    format_schema,
    LISTING_SCHEMA,
)
from .base import ModelProvider


# Phone number pattern (Iraqi mobile: 07XX XXX XXX) — stripped before sending to model
PHONE_RE = re.compile(
    r"(?:\+?964\s?)?(?:0)?(7\d{2})\s*\d{1,2}\s*\d{1,3}\s*\d{1,3}"
)

# User ID patterns — Facebook pfbid and numeric user IDs
FBID_RE = re.compile(r"pfbid[0-9A-Za-z]+")
USER_ID_RE = re.compile(r"\b\d{15,}\b")


def _strip_pii(text: str) -> str:
    """Remove phone numbers and user IDs from text before sending to model."""
    text = PHONE_RE.sub("[PHONE]", text)
    text = FBID_RE.sub("[USER]", text)
    text = USER_ID_RE.sub("[USER]", text)
    return text


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: Any = None) -> Any:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _extract_json_from_text(text: str) -> str:
    """Extract JSON object from model response text, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences
    if text.startswith("```"):
        parts = text.split("```", 2)
        if len(parts) >= 3:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    # Find the first { and last } to extract JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text.strip()


def _attempt_json_repair(text: str) -> Optional[Dict[str, Any]]:
    """Attempt a single repair of malformed JSON.

    Common fixes:
    - Trailing commas before }
    - Single quotes instead of double quotes
    - Missing closing brace
    - Unescaped newlines in strings
    """
    import re as _re

    repaired = text.strip()

    # Remove trailing commas before closing brace/bracket
    repaired = _re.sub(r",\s*}", "}", repaired)
    repaired = _re.sub(r",\s*\]", "]", repaired)

    # Replace single quotes with double quotes (but not inside strings)
    # This is a heuristic; may not work for all cases
    if "'" in repaired and '"' not in repaired:
        repaired = repaired.replace("'", '"')

    # Try to add missing closing brace
    open_count = repaired.count("{")
    close_count = repaired.count("}")
    if open_count > close_count:
        repaired += "}" * (open_count - close_count)

    try:
        return json.loads(repaired)
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_and_repair_json(
    raw_content: Optional[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse JSON from model response with single repair attempt.

    Returns (parsed_dict_or_None, error_message_or_None).
    """
    if not raw_content:
        return None, "Empty response from model"

    # Extract JSON from text (handle markdown fences)
    json_text = _extract_json_from_text(raw_content)

    # First attempt: direct parse
    try:
        return json.loads(json_text), None
    except (json.JSONDecodeError, ValueError):
        pass

    # Second attempt: single repair
    repaired = _attempt_json_repair(json_text)
    if repaired is not None:
        return repaired, None

    return None, f"Failed to parse JSON after repair attempt. Raw: {raw_content[:200]}"


def _resolve_category_key(
    parsed: Dict[str, Any],
) -> Tuple[str, Optional[str]]:
    """Resolve the classification category from parsed JSON.

    Supports both "category" and "listing_type" keys. "listing_type" is the
    canonical schema key; "category" is accepted for backward compatibility.

    Returns (category_value, conflict_note_or_None).
    - If only one key present: use it.
    - If both present and equal: use that value.
    - If both present and different: use listing_type, note the conflict.
    - If neither present: "unclear".
    """
    valid_categories = {
        "for_sale",
        "for_rent",
        "buy_or_rent_request",
        "real_estate_service",
        "not_real_estate",
        "unclear",
    }
    category_val = parsed.get("category")
    listing_type_val = parsed.get("listing_type")

    category_val = category_val if category_val in valid_categories else None
    listing_type_val = listing_type_val if listing_type_val in valid_categories else None

    if category_val is not None and listing_type_val is not None:
        if category_val == listing_type_val:
            return category_val, None
        return listing_type_val, f"category={category_val}, listing_type={listing_type_val}"
    if listing_type_val is not None:
        return listing_type_val, None
    if category_val is not None:
        return category_val, None
    return "unclear", None


class KiloProvider(ModelProvider):
    """Kilo AI Gateway cloud model provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = os.environ.get(
            "KILO_GATEWAY_BASE_URL", "https://api.kilo.ai/api/gateway"
        ).rstrip("/")
        self.model_id = os.environ.get(
            "KILO_GATEWAY_MODEL", "kilo-auto/free"
        )
        self.api_key = os.environ.get("KILO_API_KEY", "")
        self._available: Optional[bool] = None
        # Token/cost tracking
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.request_count: int = 0
        # Response diagnostics
        self.last_finish_reason: Optional[str] = None
        self.last_response_truncated: bool = False
        self.last_raw_content: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return f"Kilo AI Gateway / {self.model_id}"

    def initialize(self) -> bool:
        """Check if the Kilo AI Gateway is reachable and API key is set."""
        if not self.api_key:
            self._available = False
            return False
        self._available = self._probe_server()
        return self._available

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self.initialize()
        return self._available

    def _probe_server(self) -> bool:
        """Probe the models endpoint to verify connectivity."""
        try:
            import urllib.request as urllib_request

            url = f"{self.base_url}/models"
            req = urllib_request.Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {self.api_key}")
            with urllib_request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Send a chat completion request to Kilo AI Gateway.

        Returns the full response JSON including usage and finish_reason.
        """
        import urllib.request as urllib_request

        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)

        # Track diagnostics
        self.last_raw_content = None
        self.last_finish_reason = None
        self.last_response_truncated = False

        choices = result.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            self.last_raw_content = msg.get("content", "")
            self.last_finish_reason = choices[0].get("finish_reason")
            self.last_response_truncated = (
                self.last_finish_reason == "length"
            )

        # Track usage
        self.request_count += 1
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

        # Estimate cost (per 1K tokens)
        pricing = self._get_model_pricing()
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        self.total_cost_usd += prompt_cost + completion_cost

        return result

    def _track_usage(self, response: Dict[str, Any]) -> None:
        """Usage tracking is done in _chat directly."""
        pass

    def _get_model_pricing(self) -> Dict[str, float]:
        """Return per-1K-token pricing for the configured model."""
        pricing_table: Dict[str, Dict[str, float]] = {
            "kilo-auto/free": {"prompt": 0.0, "completion": 0.0},
            "kilo-auto/small": {
                "prompt": 0.00000005,
                "completion": 0.0000004,
            },
            "stealth/qwen3.6-plus": {
                "prompt": 0.00000025,
                "completion": 0.0000015,
            },
            "openai/gpt-3.5-turbo": {
                "prompt": 0.0000005,
                "completion": 0.0000015,
            },
            "openai/gpt-4": {"prompt": 0.00003, "completion": 0.00006},
        }
        return pricing_table.get(
            self.model_id, {"prompt": 0.000001, "completion": 0.000002}
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """Return cost tracking summary."""
        return {
            "provider": self.provider_name,
            "model": self.model_id,
            "requests": self.request_count,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "estimated_cost_usd": round(self.total_cost_usd, 6),
        }

    def get_response_diagnostics(self) -> Dict[str, Any]:
        """Return last response diagnostics."""
        return {
            "finish_reason": self.last_finish_reason,
            "truncated": self.last_response_truncated,
            "raw_content_length": len(self.last_raw_content) if self.last_raw_content else 0,
        }

    # ------------------------------------------------------------------
    # Method A: Classify then extract
    # ------------------------------------------------------------------

    def classify(self, text: str) -> Dict[str, Any]:
        """Classify a post into a listing category (Method A step 1)."""
        if not self.is_available():
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": "Kilo AI Gateway not available",
                "parse_error": None,
                "finish_reason": None,
                "truncated": False,
            }

        safe_text = _strip_pii(text)
        prompt = get_classify_prompt(safe_text)

        try:
            response = self._chat(
                [{"role": "user", "content": prompt}], max_tokens=256
            )
            content = response["choices"][0]["message"]["content"]
            parsed, parse_error = _parse_and_repair_json(content)

            if parsed is None:
                return {
                    "category": "unclear",
                    "confidence": 0.0,
                    "reasoning": f"Parse error: {parse_error}",
                    "parse_error": parse_error,
                    "finish_reason": self.last_finish_reason,
                    "truncated": self.last_response_truncated,
                }

            category = parsed.get("category", "unclear")
            valid_categories = [
                "for_sale",
                "for_rent",
                "buy_or_rent_request",
                "real_estate_service",
                "not_real_estate",
                "unclear",
            ]
            if category not in valid_categories:
                category = "unclear"

            return {
                "category": category,
                "confidence": _safe_float(parsed.get("confidence", 0.0)),
                "reasoning": parsed.get("reasoning", ""),
                "parse_error": None,
                "finish_reason": self.last_finish_reason,
                "truncated": self.last_response_truncated,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": f"Model call failed: {exc}",
                "parse_error": str(exc),
                "finish_reason": self.last_finish_reason,
                "truncated": self.last_response_truncated,
            }

    def extract(self, text: str, category: str) -> Dict[str, Any]:
        """Extract structured fields from a post (Method A step 2)."""
        if not self.is_available():
            return {
                "error": "Kilo AI Gateway not available",
                "confidence": 0.0,
                "parse_error": None,
                "finish_reason": None,
                "truncated": False,
            }

        safe_text = _strip_pii(text)
        prompt = get_extract_prompt(safe_text, category)

        try:
            response = self._chat(
                [{"role": "user", "content": prompt}], max_tokens=1024
            )
            content = response["choices"][0]["message"]["content"]
            parsed, parse_error = _parse_and_repair_json(content)

            if parsed is None:
                return {
                    "error": parse_error,
                    "confidence": 0.0,
                    "parse_error": parse_error,
                    "finish_reason": self.last_finish_reason,
                    "truncated": self.last_response_truncated,
                }

            # Map model output to schema fields with safe type conversion
            extraction: Dict[str, Any] = {
                "listing_type": parsed.get("listing_type") or category,
                "property_type": parsed.get("property_type"),
                "title": parsed.get("title"),
                "description": parsed.get("description"),
                "city": parsed.get("city"),
                "district": parsed.get("district"),
                "complex_name": parsed.get("complex_name"),
                "area_sqm": _safe_int(parsed.get("area_sqm")),
                "bedrooms": _safe_int(parsed.get("bedrooms")),
                "bathrooms": _safe_int(parsed.get("bathrooms")),
                "floor": parsed.get("floor"),
                "furnished": parsed.get("furnished"),
                "price": _safe_float(parsed.get("price")) if parsed.get("price") is not None else None,
                "currency": parsed.get("currency"),
                "contact_phones": parsed.get("contact_phones") or [],
                "published_at": parsed.get("published_at"),
                "confidence": _safe_float(parsed.get("confidence", 0.0)),
                "parse_error": None,
                "finish_reason": self.last_finish_reason,
                "truncated": self.last_response_truncated,
            }
            return extraction
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Model call failed: {exc}",
                "confidence": 0.0,
                "parse_error": str(exc),
                "finish_reason": self.last_finish_reason,
                "truncated": self.last_response_truncated,
            }

    # ------------------------------------------------------------------
    # Method B: Single call for both classification and extraction
    # ------------------------------------------------------------------

    def classify_and_extract(self, text: str) -> Dict[str, Any]:
        """Classify and extract in a single API call (Method B).

        Returns a dict with keys:
            - category: resolved classification category
            - confidence: float 0.0-1.0
            - reasoning: model reasoning (may be empty)
            - status: one of "ok", "model_unclear", "parse_error", "truncated",
                      "schema_error", "api_error"
            - conflict_note: None or description of category/listing_type conflict
            - finish_reason: API finish_reason
            - truncated: whether response was truncated
            - extraction: extraction dict or None
        """
        if not self.is_available():
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": "Kilo AI Gateway not available",
                "status": "api_error",
                "conflict_note": None,
                "finish_reason": None,
                "truncated": False,
                "extraction": None,
            }

        safe_text = _strip_pii(text)
        prompt = get_combined_prompt(safe_text)

        try:
            response = self._chat(
                [{"role": "user", "content": prompt}], max_tokens=2048
            )
            content = response["choices"][0]["message"]["content"]
            truncated = self.last_response_truncated
            finish_reason = self.last_finish_reason

            # If truncated, do not attempt JSON repair — report as truncated
            if truncated:
                return {
                    "category": "unclear",
                    "confidence": 0.0,
                    "reasoning": "Response truncated before complete JSON",
                    "status": "truncated",
                    "conflict_note": None,
                    "finish_reason": finish_reason,
                    "truncated": True,
                    "extraction": None,
                }

            parsed, parse_error = _parse_and_repair_json(content)

            if parsed is None:
                return {
                    "category": "unclear",
                    "confidence": 0.0,
                    "reasoning": f"Parse error: {parse_error}",
                    "status": "parse_error",
                    "conflict_note": None,
                    "finish_reason": finish_reason,
                    "truncated": False,
                    "extraction": None,
                }

            # Resolve category from either "category" or "listing_type" key
            category, conflict_note = _resolve_category_key(parsed)

            extraction: Dict[str, Any] = {
                "listing_type": category,
                "property_type": parsed.get("property_type"),
                "title": parsed.get("title"),
                "description": parsed.get("description"),
                "city": parsed.get("city"),
                "district": parsed.get("district"),
                "complex_name": parsed.get("complex_name"),
                "area_sqm": _safe_int(parsed.get("area_sqm")),
                "bedrooms": _safe_int(parsed.get("bedrooms")),
                "bathrooms": _safe_int(parsed.get("bathrooms")),
                "floor": parsed.get("floor"),
                "furnished": parsed.get("furnished"),
                "price": _safe_float(parsed.get("price")) if parsed.get("price") is not None else None,
                "currency": parsed.get("currency"),
                "contact_phones": parsed.get("contact_phones") or [],
                "published_at": parsed.get("published_at"),
                "confidence": _safe_float(parsed.get("confidence", 0.0)),
                "status": "ok",
                "conflict_note": conflict_note,
                "finish_reason": finish_reason,
                "truncated": truncated,
            }

            return {
                "category": category,
                "confidence": _safe_float(parsed.get("confidence", 0.0)),
                "reasoning": parsed.get("reasoning", ""),
                "status": "ok",
                "conflict_note": conflict_note,
                "finish_reason": finish_reason,
                "truncated": truncated,
                "extraction": extraction,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": f"Model call failed: {exc}",
                "status": "api_error",
                "conflict_note": None,
                "finish_reason": self.last_finish_reason,
                "truncated": self.last_response_truncated,
                "extraction": None,
            }
