"""Local rule-based provider for testing without a model server.

Uses regex and keyword matching to classify posts and extract
structured fields. Intended for offline testing and as a fallback
when the Kilo model server is unavailable.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from .base import ModelProvider

# Eastern Arabic numerals mapping
ARABIC_NUMERALS = {
    "\u0660": "0",
    "\u0661": "1",
    "\u0662": "2",
    "\u0663": "3",
    "\u0664": "4",
    "\u0665": "5",
    "\u0666": "6",
    "\u0667": "7",
    "\u0668": "8",
    "\u0669": "9",
}

# Alef normalization: map all alef variants to plain alef (ا)
ALEF_VARIANTS = {
    "\u0622": "\u0627",  # آ -> ا
    "\u0623": "\u0627",  # أ -> ا
    "\u0625": "\u0627",  # إ -> ا
    "\u0649": "\u0627",  # ى -> ا
}

# Digit character class: Western + Eastern Arabic-Indic digits
_DIGIT = r"[0-9\u0660-\u0669]"

# Phone number patterns (Iraqi mobile: 07XX XXX XXX = 11 digits)
# Handles spaces between groups: 0773 222 91 42
PHONE_RE = re.compile(
    r"(?:\+?964\s?)?(?:0)?(7" + _DIGIT + r"{2})\s*" + _DIGIT + r"{1,2}\s*" + _DIGIT + r"{1,3}\s*" + _DIGIT + r"{1,3}"
)

# Price patterns
PRICE_RE = re.compile(
    r"(?:السعر|price|سعر)\s*[:=]?\s*(" + _DIGIT + r"[\d,\u0660-\u0669.]*)\s*(دولار|USD|دينار|IQD)?",
    re.IGNORECASE,
)

# Area patterns: handles "125 متر", "125م", "١٢٥ متر", "١٢٥م"
AREA_RE = re.compile(
    r"(" + _DIGIT + r"[\d,\u0660-\u0669.]*)\s*(متر|م²|m2|sqm|متر مربع|\u0645)",
    re.IGNORECASE,
)

# Bedroom patterns
BEDROOM_RE = re.compile(
    r"(" + _DIGIT + r"[\d,\u0660-\u0669.]*)\s*(غرفة|غرف|bedroom|bedrooms|نوم)",
    re.IGNORECASE,
)

# Category keywords (normalized to plain alef for matching)
FOR_SALE_KEYWORDS = [
    "للبيع", "for sale", "فرۆشتن", "دار للبيع",
    "شقة للبيع", "بيت للبيع",
]
FOR_RENT_KEYWORDS = [
    "للإيجار", "for rent", "ايجار", "مفروشة للأيجار",
    "شقة للأيجار", "للإيجار داخل", "للايجار", "للأيجار",
]
SERVICE_KEYWORDS = [
    "مقاول", "contractor", "حديقجي", "gardening", "تفليش", "تعمير",
    "سياج", "زراعة", "تصميم", "ديكورات",
]
BUY_REQUEST_KEYWORDS = [
    "أبحث عن", "بحث عن", "أريد شراء", "أريد إيجار",
    "Looking for", "buy", "rent request",
]


def _normalize_alef(text: str) -> str:
    """Normalize Arabic alef variants to plain alef (ا)."""
    result = []
    for ch in text:
        result.append(ALEF_VARIANTS.get(ch, ch))
    return "".join(result)


def _normalize_arabic_numerals(text: str) -> str:
    """Convert Eastern Arabic numerals to Western digits."""
    result = []
    for ch in text:
        result.append(ARABIC_NUMERALS.get(ch, ch))
    return "".join(result)


def _normalize_text(text: str) -> str:
    """Full Arabic text normalization: lowercase + alef normalization."""
    return _normalize_alef(text.lower())


def _extract_phones(text: str) -> List[str]:
    """Extract Iraqi phone numbers from text."""
    phones: List[str] = []
    for match in PHONE_RE.finditer(text):
        full = match.group(0)
        normalized = _normalize_arabic_numerals(full)
        # Clean up spaces
        normalized = re.sub(r"\s+", "", normalized)
        # Must be 10 or 11 digits
        if len(normalized) >= 10 and normalized not in phones:
            phones.append(normalized)
    return phones


def _extract_number(text: str, pattern: re.Pattern) -> Optional[int]:
    """Extract first integer match from text using pattern."""
    match = pattern.search(text)
    if not match:
        return None
    num_str = _normalize_arabic_numerals(match.group(1))
    num_str = re.sub(r"[,\.]", "", num_str)
    try:
        return int(num_str)
    except ValueError:
        return None


class LocalProvider(ModelProvider):
    """Rule-based local provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._initialized = True

    @property
    def provider_name(self) -> str:
        return "Local Rule-Based Provider"

    def initialize(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def classify(self, text: str) -> Dict[str, Any]:
        text_norm = _normalize_text(text)

        # Check for service/contractor keywords first (highest priority for non-listings)
        for kw in SERVICE_KEYWORDS:
            if _normalize_alef(kw.lower()) in text_norm:
                return {
                    "category": "real_estate_service",
                    "confidence": 0.85,
                    "reasoning": f"Contains service keyword: {kw}",
                }

        # Check for rent keywords
        for kw in FOR_RENT_KEYWORDS:
            if _normalize_alef(kw.lower()) in text_norm:
                return {
                    "category": "for_rent",
                    "confidence": 0.90,
                    "reasoning": f"Contains rent keyword: {kw}",
                }

        # Check for sale keywords
        for kw in FOR_SALE_KEYWORDS:
            if _normalize_alef(kw.lower()) in text_norm:
                return {
                    "category": "for_sale",
                    "confidence": 0.90,
                    "reasoning": f"Contains sale keyword: {kw}",
                }

        # Check for buy/rent request
        for kw in BUY_REQUEST_KEYWORDS:
            if _normalize_alef(kw.lower()) in text_norm:
                return {
                    "category": "buy_or_rent_request",
                    "confidence": 0.75,
                    "reasoning": f"Contains request keyword: {kw}",
                }

        return {
            "category": "unclear",
            "confidence": 0.40,
            "reasoning": "No clear category keywords found",
        }

    def extract(self, text: str, category: str) -> Dict[str, Any]:
        phones = _extract_phones(text)
        area = _extract_number(text, AREA_RE)
        bedrooms = _extract_number(text, BEDROOM_RE)

        # Determine property type
        property_type: Optional[str] = None
        text_norm = _normalize_text(text)
        if "شقة" in text_norm or "apartment" in text_norm:
            property_type = "apartment"
        elif "بيت" in text_norm or "house" in text_norm:
            property_type = "house"
        elif "دار" in text_norm or "home" in text_norm:
            property_type = "house"
        elif "مزرعة" in text_norm or "farm" in text_norm:
            property_type = "farm"
        elif "أرض".replace("أ", "ا") in text_norm or "land" in text_norm or "قطعة" in text_norm:
            property_type = "land"
        elif "فيلا" in text_norm or "villa" in text_norm:
            property_type = "villa"

        # Determine furnished status
        furnished: Optional[bool] = None
        if "مفروشة" in text_norm or "furnished" in text_norm:
            furnished = True
        elif "فارغ" in text_norm or "unfurnished" in text_norm:
            furnished = False

        # Determine city
        city: Optional[str] = None
        if "اربيل" in text_norm or "أربيل".replace("أ", "ا") in text_norm or "erbil" in text_norm:
            city = "أربيل"
        elif "بغداد" in text_norm or "baghdad" in text_norm:
            city = "بغداد"

        # Determine complex name (look for "مجمع X")
        complex_name: Optional[str] = None
        complex_match = re.search(
            r"مجمع\s+([^\n,;]+)", text, re.IGNORECASE
        )
        if complex_match:
            complex_name = complex_match.group(1).strip()

        # Determine district (look for "على شارع X" or "في منطقة X")
        district: Optional[str] = None
        district_match = re.search(
            r"(?:على|في)\s+(شارع\s+[\u0621-\u064A0-9\s\u0660-\u0669]+?)(?:\s|$|,|;|\n)",
            text, re.IGNORECASE
        )
        if district_match:
            district = district_match.group(1).strip()

        # Extract price
        price: Optional[float] = None
        currency: Optional[str] = None
        price_match = PRICE_RE.search(text)
        if price_match:
            try:
                price_str = _normalize_arabic_numerals(price_match.group(1))
                price_str = re.sub(r"[,\.]", "", price_str)
                price = float(price_str)
            except ValueError:
                price = None
            currency = price_match.group(2) if price_match.lastindex >= 2 else None

        # Build title
        title_parts: List[str] = []
        if property_type:
            title_parts.append(property_type)
        if city:
            title_parts.append(f"في {city}")
        if complex_name:
            title_parts.append(f"مجمع {complex_name}")
        if category in ("for_sale", "for_rent"):
            title_parts.append("للبيع" if category == "for_sale" else "للإيجار")
        title = " ".join(title_parts) if title_parts else None

        return {
            "listing_type": category,
            "property_type": property_type,
            "title": title,
            "description": text[:500],
            "city": city,
            "district": district,
            "complex_name": complex_name,
            "area_sqm": area,
            "bedrooms": bedrooms,
            "bathrooms": None,
            "floor": None,
            "furnished": furnished,
            "price": price,
            "currency": currency,
            "contact_phones": phones,
            "published_at": None,
            "confidence": 0.70,
        }
