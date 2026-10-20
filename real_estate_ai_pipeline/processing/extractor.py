"""Data extractor: extracts structured listing fields from post text."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from providers.base import ModelProvider


class ListingExtractor:
    """Extracts structured fields from classified posts using a model provider."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    def extract_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured fields from a single post.

        Only extracts for posts classified as for_sale or for_rent.
        Returns the post with _extraction results added.
        """
        category = post.get("_classification", {}).get("category", "unclear")
        text = post.get("text", "")

        if category not in ("for_sale", "for_rent"):
            post["_extraction"] = {
                "skipped": True,
                "reason": f"Category '{category}' is not a sale/rent listing",
                "confidence": 0.0,
            }
            return post

        result = self.provider.extract(text, category)

        # Merge with source metadata
        extraction: Dict[str, Any] = {
            "skipped": False,
            "provider": self.provider.provider_name,
            "confidence": float(result.get("confidence", 0.0)),
        }

        # Map model output to schema fields
        schema_fields = [
            "listing_type", "property_type", "title", "description",
            "city", "district", "complex_name", "area_sqm", "bedrooms",
            "bathrooms", "floor", "furnished", "price", "currency",
            "contact_phones", "published_at",
        ]
        for field in schema_fields:
            extraction[field] = result.get(field)

        # Override contact_phones with locally extracted phones if model didn't provide
        if not extraction.get("contact_phones"):
            phones = self._extract_phones_locally(text)
            extraction["contact_phones"] = phones

        # Ensure source fields
        extraction["source"] = "facebook_group"
        extraction["source_url"] = post.get("url")
        extraction["published_at"] = post.get("time")

        post["_extraction"] = extraction
        return post

    def extract_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract fields from all posts."""
        return [self.extract_post(post) for post in posts]

    @staticmethod
    def _extract_phones_locally(text: str) -> List[str]:
        """Extract phone numbers using regex fallback."""
        phones: List[str] = []
        pattern = re.compile(
            r"(?:\+?964\s?)?(?:0)?(7[0-9]{2})\s?(\d{3})\s?(\d{4})"
        )
        for match in pattern.finditer(text):
            phone = match.group(0)
            phone = re.sub(r"\s+", "", phone)
            if phone not in phones:
                phones.append(phone)
        return phones
