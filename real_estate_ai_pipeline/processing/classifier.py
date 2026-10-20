"""Post classifier: categorizes Facebook posts into listing types."""

from __future__ import annotations

from typing import Any, Dict, List

from providers.base import ModelProvider


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# Valid listing categories
CATEGORIES = [
    "for_sale",
    "for_rent",
    "buy_or_rent_request",
    "real_estate_service",
    "not_real_estate",
    "unclear",
]


class PostClassifier:
    """Classifies Facebook posts using a model provider."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    def classify_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a single post.

        Adds classification results to the post dict.
        """
        text = post.get("text", "")
        result = self.provider.classify(text)

        category = result.get("category", "unclear")
        if category not in CATEGORIES:
            category = "unclear"

        post["_classification"] = {
            "category": category,
            "confidence": _safe_float(result.get("confidence", 0.0)),
            "reasoning": result.get("reasoning", ""),
            "provider": self.provider.provider_name,
        }
        return post

    def classify_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify all posts."""
        return [self.classify_post(post) for post in posts]

    def is_real_estate(self, category: str) -> bool:
        """Check if a category represents a real estate listing (sale/rent)."""
        return category in ("for_sale", "for_rent")

    def is_service(self, category: str) -> bool:
        """Check if a category is a real estate service."""
        return category == "real_estate_service"
