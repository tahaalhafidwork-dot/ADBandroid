"""Deduplicator: detects duplicate posts at two levels.

Level 1: Exact match on post URL or ID.
Level 2: Similarity on text, location, area, property type, and contact phones.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

try:
    from difflib import SequenceMatcher
except ImportError:  # pragma: no cover
    SequenceMatcher = None


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    if SequenceMatcher:
        return SequenceMatcher(None, a, b).ratio()
    # Fallback: simple word overlap
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _phones_overlap(phones_a: List[str], phones_b: List[str]) -> bool:
    """Check if two phone lists share any number."""
    set_a = set(p.strip() for p in phones_a if p)
    set_b = set(p.strip() for p in phones_b if p)
    return bool(set_a & set_b)


class Deduplicator:
    """Detects duplicate posts at two levels."""

    def __init__(self, similarity_threshold: float = 0.80):
        self.threshold = similarity_threshold

    def find_duplicates(
        self, posts: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split posts into unique and duplicate lists.

        Returns (unique_posts, duplicate_posts).
        """
        seen_urls: set = set()
        seen_ids: set = set()
        unique: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []

        for post in posts:
            # Support both "url" and "source_url" fields
            post_url = post.get("url") or post.get("source_url", "")
            post_id = self._extract_post_id(post_url)

            # Level 1: URL or ID match
            if post_url in seen_urls or (post_id and post_id in seen_ids):
                dup = dict(post)
                dup["_duplicate_reason"] = (
                    f"Level 1: duplicate URL or ID (url={post_url})"
                )
                dup["_duplicate_confidence"] = 1.0
                duplicates.append(dup)
                continue

            # Level 2: similarity check against existing unique posts
            is_dup = False
            best_reason = ""
            best_confidence = 0.0

            for existing in unique:
                similarity = self._compute_similarity(post, existing)
                if similarity >= self.threshold:
                    is_dup = True
                    best_reason = (
                        f"Level 2: similar post (similarity={similarity:.2f}, "
                        f"existing_url={existing.get('url')})"
                    )
                    best_confidence = similarity
                    break

            if is_dup:
                dup = dict(post)
                dup["_duplicate_reason"] = best_reason
                dup["_duplicate_confidence"] = best_confidence
                duplicates.append(dup)
            else:
                seen_urls.add(post_url)
                if post_id:
                    seen_ids.add(post_id)
                unique.append(post)

        return unique, duplicates

    def _extract_post_id(self, url: str) -> str:
        """Extract Facebook post ID from URL."""
        match = re.search(r"/permalink/(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/(\d+)(?:/|\?|$)", url)
        if match:
            return match.group(1)
        return ""

    def _compute_similarity(
        self, post_a: Dict[str, Any], post_b: Dict[str, Any]
    ) -> float:
        """Compute composite similarity between two posts."""
        scores = []

        # Text similarity
        text_a = post_a.get("text", "") or post_a.get("description", "")
        text_b = post_b.get("text", "") or post_b.get("description", "")
        text_sim = _text_similarity(text_a, text_b)
        scores.append(("text", text_sim, 0.4))

        # Location similarity (city + district + complex)
        ext_a = post_a.get("_extraction") or post_a
        ext_b = post_b.get("_extraction") or post_b
        loc_sim = self._location_similarity(ext_a, ext_b)
        scores.append(("location", loc_sim, 0.2))

        # Area similarity
        area_sim = self._numeric_similarity(
            ext_a.get("area_sqm"), ext_b.get("area_sqm")
        )
        scores.append(("area", area_sim, 0.15))

        # Property type similarity
        type_sim = 1.0 if ext_a.get("property_type") == ext_b.get("property_type") and ext_a.get("property_type") else 0.0
        scores.append(("property_type", type_sim, 0.15))

        # Phone overlap
        phones_sim = 1.0 if _phones_overlap(
            ext_a.get("contact_phones", []), ext_b.get("contact_phones", [])
        ) else 0.0
        scores.append(("phones", phones_sim, 0.1))

        # Weighted average
        total_weight = sum(w for _, _, w in scores)
        weighted_sum = sum(s * w for _, s, w in scores)
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    @staticmethod
    def _location_similarity(ext_a: Dict[str, Any], ext_b: Dict[str, Any]) -> float:
        """Compare location fields."""
        matches = 0
        total = 0
        for field in ("city", "district", "complex_name"):
            val_a = ext_a.get(field)
            val_b = ext_b.get(field)
            total += 1
            if val_a and val_b and val_a == val_b:
                matches += 1
            elif not val_a and not val_b:
                matches += 1  # Both missing counts as match
        return matches / total if total > 0 else 0.0

    @staticmethod
    def _numeric_similarity(val_a: Any, val_b: Any) -> float:
        """Compare two numeric values."""
        if val_a is None or val_b is None:
            return 0.5  # Unknown
        try:
            a = float(val_a)
            b = float(val_b)
            if a == 0 and b == 0:
                return 1.0
            if a == 0 or b == 0:
                return 0.0
            diff = abs(a - b) / max(a, b)
            return max(0.0, 1.0 - diff)
        except (ValueError, TypeError):
            return 0.0
