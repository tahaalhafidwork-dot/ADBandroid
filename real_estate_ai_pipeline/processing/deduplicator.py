"""Deduplicator: detects duplicate posts at multiple levels.

Level 1: Exact match on post URL or ID.
Level 2: Normalized text fingerprint match.
Level 3: Similarity on text, location, area, property type, and contact phones.
Level 4: Same phone + same complex + same city (agent posting multiple units).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from difflib import SequenceMatcher
except ImportError:  # pragma: no cover
    SequenceMatcher = None


def _normalize_text_for_fingerprint(text: str) -> str:
    """Normalize text for fingerprint comparison.

    Removes punctuation, extra whitespace, emojis, and normalizes
    Arabic numerals to Western digits for comparison.
    """
    if not text:
        return ""
    # Convert Eastern Arabic numerals to Western
    arabic_numerals = {
        "\u0660": "0", "\u0661": "1", "\u0662": "2", "\u0663": "3", "\u0664": "4",
        "\u0665": "5", "\u0666": "6", "\u0667": "7", "\u0668": "8", "\u0669": "9",
    }
    normalized = []
    for ch in text:
        normalized.append(arabic_numerals.get(ch, ch))
    text = "".join(normalized)
    # Remove emojis and special characters, keep alphanumeric and Arabic
    text = re.sub(r"[^\u0621-\u064A\u0660-\u0669a-zA-Z0-9\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _text_fingerprint(text: str) -> str:
    """Create a fingerprint of the text for exact-ish matching."""
    return _normalize_text_for_fingerprint(text)


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    if SequenceMatcher:
        return SequenceMatcher(None, a, b).ratio()
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
    """Detects duplicate posts at four levels."""

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        fingerprint_threshold: float = 0.90,
    ):
        self.similarity_threshold = similarity_threshold
        self.fingerprint_threshold = fingerprint_threshold

    def find_duplicates(
        self, posts: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split posts into unique and duplicate lists.

        Returns (unique_posts, duplicate_posts).
        """
        seen_urls: set = set()
        seen_ids: set = set()
        seen_fingerprints: dict = {}  # fingerprint -> first post index
        unique: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []

        for post in posts:
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

            # Level 2: Normalized text fingerprint match
            fp = _text_fingerprint(post.get("text", ""))
            if fp and fp in seen_fingerprints:
                existing_idx = seen_fingerprints[fp]
                dup = dict(post)
                dup["_duplicate_reason"] = (
                    f"Level 2: identical text fingerprint "
                    f"(matches post index {existing_idx})"
                )
                dup["_duplicate_confidence"] = 1.0
                duplicates.append(dup)
                continue

            # Level 3: Similarity check against existing unique posts
            is_dup = False
            best_reason = ""
            best_confidence = 0.0

            for existing in unique:
                similarity = self._compute_similarity(post, existing)
                if similarity >= self.similarity_threshold:
                    is_dup = True
                    best_reason = (
                        f"Level 3: similar post "
                        f"(similarity={similarity:.2f}, "
                        f"existing_url={existing.get('url') or existing.get('source_url')})"
                    )
                    best_confidence = similarity
                    break

            # Level 4: Same phone + same complex + same city
            if not is_dup:
                level4 = self._check_level4_duplicate(post, unique)
                if level4[0]:
                    is_dup = True
                    best_reason = level4[1]
                    best_confidence = level4[2]

            if is_dup:
                dup = dict(post)
                dup["_duplicate_reason"] = best_reason
                dup["_duplicate_confidence"] = best_confidence
                duplicates.append(dup)
            else:
                seen_urls.add(post_url)
                if post_id:
                    seen_ids.add(post_id)
                if fp:
                    seen_fingerprints[fp] = len(unique)
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

        # Text similarity (highest weight)
        text_a = post_a.get("text", "") or post_a.get("description", "")
        text_b = post_b.get("text", "") or post_b.get("description", "")
        text_sim = _text_similarity(text_a, text_b)
        scores.append(("text", text_sim, 0.5))

        # Location similarity
        ext_a = post_a.get("_extraction") or post_a
        ext_b = post_b.get("_extraction") or post_b
        loc_sim = self._location_similarity(ext_a, ext_b)
        scores.append(("location", loc_sim, 0.15))

        # Area similarity
        area_sim = self._numeric_similarity(
            ext_a.get("area_sqm"), ext_b.get("area_sqm")
        )
        scores.append(("area", area_sim, 0.15))

        # Property type similarity
        type_sim = (
            1.0
            if ext_a.get("property_type") == ext_b.get("property_type")
            and ext_a.get("property_type")
            else 0.0
        )
        scores.append(("property_type", type_sim, 0.1))

        # Phone overlap
        phones_sim = (
            1.0
            if _phones_overlap(
                ext_a.get("contact_phones", []), ext_b.get("contact_phones", [])
            )
            else 0.0
        )
        scores.append(("phones", phones_sim, 0.1))

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
                matches += 1
        return matches / total if total > 0 else 0.0

    @staticmethod
    def _numeric_similarity(val_a: Any, val_b: Any) -> float:
        """Compare two numeric values."""
        if val_a is None or val_b is None:
            return 0.5
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

    @staticmethod
    def _check_level4_duplicate(
        post: Dict[str, Any], unique: List[Dict[str, Any]]
    ) -> Tuple[bool, str, float]:
        """Check if same phone + same complex + same city indicates duplicate."""
        ext = post.get("_extraction") or post
        phones = set(p.strip() for p in ext.get("contact_phones", []) if p)
        complex_name = ext.get("complex_name")
        city = ext.get("city")

        if not phones:
            return False, "", 0.0

        for existing in unique:
            ext_existing = existing.get("_extraction") or existing
            existing_phones = set(
                p.strip() for p in ext_existing.get("contact_phones", []) if p
            )
            existing_complex = ext_existing.get("complex_name")
            existing_city = ext_existing.get("city")

            # Same phone AND same complex AND same city
            if phones & existing_phones:
                if complex_name and existing_complex and complex_name == existing_complex:
                    if city and existing_city and city == existing_city:
                        return (
                            True,
                            "Level 4: same phone + same complex + same city",
                            0.85,
                        )
                # Same phone + same complex (even if city missing)
                if complex_name and existing_complex and complex_name == existing_complex:
                    return (
                        True,
                        "Level 4: same phone + same complex",
                        0.75,
                    )

        return False, "", 0.0
