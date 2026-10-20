"""Data normalizer: normalizes extracted listing fields."""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Arabic numeral mapping for normalization
ARABIC_NUMERALS = {
    "\u0660": "0", "\u0661": "1", "\u0662": "2", "\u0663": "3", "\u0664": "4",
    "\u0665": "5", "\u0666": "6", "\u0667": "7", "\u0668": "8", "\u0669": "9",
}


def _normalize_numerals(text: str) -> str:
    """Convert Eastern Arabic numerals to Western digits."""
    return "".join(ARABIC_NUMERALS.get(ch, ch) for ch in text)


class ListingNormalizer:
    """Normalizes extracted listing fields to consistent formats."""

    def normalize(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single listing dict. Returns a new dict."""
        normalized = dict(listing)

        # Normalize area_sqm
        if listing.get("area_sqm") is not None:
            try:
                normalized["area_sqm"] = int(listing["area_sqm"])
            except (ValueError, TypeError):
                normalized["area_sqm"] = None

        # Normalize bedrooms
        if listing.get("bedrooms") is not None:
            try:
                normalized["bedrooms"] = int(listing["bedrooms"])
            except (ValueError, TypeError):
                normalized["bedrooms"] = None

        # Normalize bathrooms
        if listing.get("bathrooms") is not None:
            try:
                normalized["bathrooms"] = int(listing["bathrooms"])
            except (ValueError, TypeError):
                normalized["bathrooms"] = None

        # Normalize price
        if listing.get("price") is not None:
            try:
                normalized["price"] = float(listing["price"])
            except (ValueError, TypeError):
                normalized["price"] = None

        # Normalize furnished (ensure boolean or None)
        furnished = listing.get("furnished")
        if isinstance(furnished, str):
            furnished_lower = furnished.strip().lower()
            if furnished_lower in ("true", "yes", "1", "مفروشة", "مؤثثة"):
                normalized["furnished"] = True
            elif furnished_lower in ("false", "no", "0", "فارغ", "غير مفروشة"):
                normalized["furnished"] = False
            else:
                normalized["furnished"] = None
        elif furnished is not None:
            normalized["furnished"] = bool(furnished)

        # Normalize contact_phones
        phones = listing.get("contact_phones") or []
        normalized_phones = []
        for phone in phones:
            if phone:
                normalized_phone = re.sub(r"\s+", "", str(phone))
                if normalized_phone and normalized_phone not in normalized_phones:
                    normalized_phones.append(normalized_phone)
        normalized["contact_phones"] = normalized_phones

        # Normalize confidence
        if listing.get("confidence") is not None:
            try:
                conf = float(listing["confidence"])
                normalized["confidence"] = max(0.0, min(1.0, conf))
            except (ValueError, TypeError):
                normalized["confidence"] = None

        return normalized

    def normalize_all(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize all listings."""
        return [self.normalize(l) for l in listings]
