"""Kilo Code model provider.

Calls the locally configured Qwen 3.5 4B model server via an
OpenAI-compatible REST API at http://127.0.0.1:11436/v1.

Configuration is read from environment variables set by Kilo Code:
    XAUTAHA_MODEL_SERVER__BASE_URL   -> base URL of the model server
    XAUTAHA_MODEL_SERVER__MODEL_IDENTIFIER -> model name to use

No API keys are required for the local server. No credentials are
logged or transmitted.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .base import ModelProvider


class KiloProvider(ModelProvider):
    """Kilo Code / local OpenVINO Qwen model provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = os.environ.get(
            "XAUTAHA_MODEL_SERVER__BASE_URL", "http://127.0.0.1:11436/v1"
        ).rstrip("/")
        self.model_id = os.environ.get(
            "XAUTAHA_MODEL_SERVER__MODEL_IDENTIFIER",
            "OpenVINO/Qwen3.5-4B-int4-ov",
        )
        self._available: Optional[bool] = None

    @property
    def provider_name(self) -> str:
        return f"Kilo Code / {self.model_id}"

    def initialize(self) -> bool:
        """Check if the model server is reachable."""
        self._available = self._probe_server()
        return self._available

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._probe_server()
        return self._available

    def _probe_server(self) -> bool:
        """Probe the model server health endpoint."""
        try:
            url = f"{self.base_url}/models"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        return False

    def _chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        """Send a chat completion request to the model server."""
        payload: Dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
        return result["choices"][0]["message"]["content"]

    def classify(self, text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "category": "unclear",
                "confidence": 0.0,
                "reasoning": "Model server not available",
            }

        prompt = (
            "You are a real estate listing classifier for Arabic Facebook group posts.\n"
            "Classify the post into exactly one category:\n"
            "1. for_sale - property for sale\n"
            "2. for_rent - property for rent\n"
            "3. buy_or_rent_request - request to buy or rent\n"
            "4. real_estate_service - contractor, gardening, maintenance services\n"
            "5. not_real_estate - not related to real estate\n"
            "6. unclear - cannot determine\n\n"
            "Respond in JSON only: {\"category\": \"...\"; \"confidence\": 0.0-1.0; \"reasoning\": \"...\"}\n\n"
            f"Post text:\n{text[:2000]}"
        )

        try:
            response = self._chat([{"role": "user", "content": prompt}])
            # Try to extract JSON from the response
            result = self._parse_json(response)
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
                "error": "Model server not available",
                "confidence": 0.0,
            }

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
            "- Respond in JSON only.\n\n"
            f"Category: {category}\n"
            f"Post text:\n{text[:3000]}\n\n"
            "Output JSON with keys: listing_type, property_type, title, description, "
            "city, district, complex_name, area_sqm, bedrooms, bathrooms, floor, "
            "furnished, price, currency, contact_phones, published_at, confidence"
        )

        try:
            response = self._chat([{"role": "user", "content": prompt}], max_tokens=1024)
            result = self._parse_json(response)
            return result
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Model call failed: {exc}",
                "confidence": 0.0,
            }

    @staticmethod
    def _parse_json(response: str) -> Dict[str, Any]:
        """Parse JSON from a model response, handling markdown code fences."""
        text = response.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("```", 2)
            if len(text) >= 3:
                text = text[1]
                # Remove language hint if present
                if text.startswith("json"):
                    text = text[4:]
        text = text.strip()
        return json.loads(text)
