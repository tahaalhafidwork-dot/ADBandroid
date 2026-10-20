"""Kilo AI Gateway model provider.

Calls the Kilo AI Gateway cloud API at https://api.kilo.ai/api/gateway
using the KILO_API_KEY environment variable for authentication.

Configuration is read from environment variables:
    KILO_GATEWAY_BASE_URL   -> base URL of the Kilo AI Gateway (default: https://api.kilo.ai/api/gateway)
    KILO_API_KEY            -> authentication bearer token (required)
    KILO_GATEWAY_MODEL      -> model ID to use (default: stealth/qwen3.6-plus)

No credentials are logged or transmitted to stdout. Phone numbers and
user PII are stripped locally before sending text to the model.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

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
            url = f"{self.base_url}/models"
            req = urllib_request.Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {self.api_key}")
            with urllib_request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _chat(
        self, messages: List[Dict[str, str]], max_tokens: int = 512
    ) -> Dict[str, Any]:
        """Send a chat completion request to Kilo AI Gateway.

        Returns the full response JSON so we can extract usage/cost info.
        """
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
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
        return result

    def classify(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": "Kilo AI Gateway not available",
            }

        # Strip PII before sending to model
        safe_text = _strip_pii(text)

        prompt = (
            "You are a real estate listing classifier for Arabic Facebook group posts.\n"
            "Classify the post into exactly one category:\n"
            "1. for_sale - property for sale\n"
            "2. for_rent - property for rent\n"
            "3. buy_or_rent_request - request to buy or rent\n"
            "4. real_estate_service - contractor, gardening, maintenance services\n"
            "5. not_real_estate - not related to real estate\n"
            "6. unclear - cannot determine\n\n"
            "Rules:\n"
            "- Contractor/gardening services are NOT real estate listings for sale/rent\n"
            "- Respond in JSON only\n\n"
            f"Post text:\n{safe_text[:2000]}"
        )

        try:
            response = self._chat(
                [{"role": "user", "content": prompt}], max_tokens=256
            )
            self._track_usage(response)
            content = response["choices"][0]["message"]["content"]
            result = self._parse_json(content)
            return {
                "category": result.get("category", "unclear"),
                "confidence": float(result.get("confidence", 0.0)),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": f"Model call failed: {exc}",
            }

    def extract(self, text: str, category: str) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "error": "Kilo AI Gateway not available",
                "confidence": 0.0,
            }

        # Strip PII before sending to model
        safe_text = _strip_pii(text)

        prompt = (
            "You are a real estate data extraction assistant for Arabic Facebook posts.\n"
            "Extract structured fields from the post text below.\n"
            "Rules:\n"
            "- Do not invent prices, areas, or locations not mentioned.\n"
            "- If a field is not mentioned, use null.\n"
            "- Understand Arabic and Eastern Arabic numerals (١٢٣).\n"
            "- Support Arabic and Kurdish text in the same post.\n"
            "- Distinguish land area, building area, and garden area when clear.\n"
            "- Do not convert currencies.\n"
            "- Create a professional title without adding information not present.\n"
            "- Phone numbers are already stripped; do not extract them.\n"
            "- Respond in JSON only.\n\n"
            f"Category: {category}\n"
            f"Post text:\n{safe_text[:3000]}\n\n"
            "Output JSON with keys: listing_type, property_type, title, description, "
            "city, district, complex_name, area_sqm, bedrooms, bathrooms, floor, "
            "furnished, price, currency, contact_phones, published_at, confidence"
        )

        try:
            response = self._chat(
                [{"role": "user", "content": prompt}], max_tokens=1024
            )
            self._track_usage(response)
            content = response["choices"][0]["message"]["content"]
            result = self._parse_json(content)
            return result
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Model call failed: {exc}",
                "confidence": 0.0,
            }

    def _track_usage(self, response: Dict[str, Any]) -> None:
        """Track token usage and estimated cost from API response."""
        self.request_count += 1
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

        # Estimate cost based on model pricing (per 1K tokens)
        # stealth/qwen3.6-plus: prompt $0.00000025/token, completion $0.0000015/token
        # These are per-token prices, so multiply by token count / 1000
        pricing = self._get_model_pricing()
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        self.total_cost_usd += prompt_cost + completion_cost

    def _get_model_pricing(self) -> Dict[str, float]:
        """Return per-1K-token pricing for the configured model."""
        # Known pricing from Kilo AI Gateway models endpoint
        pricing_table: Dict[str, Dict[str, float]] = {
            "kilo-auto/free": {
                "prompt": 0.0,
                "completion": 0.0,
            },
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
            "openai/gpt-4": {
                "prompt": 0.00003,
                "completion": 0.00006,
            },
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

    @staticmethod
    def _parse_json(response: str) -> Dict[str, Any]:
        """Parse JSON from a model response, handling markdown code fences."""
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```", 2)
            if len(text) >= 3:
                text = text[1]
                if text.startswith("json"):
                    text = text[4:]
        text = text.strip()
        return json.loads(text)


# Lazy import to avoid top-level urllib.request reference issue
import urllib.request as urllib_request  # noqa: E402
