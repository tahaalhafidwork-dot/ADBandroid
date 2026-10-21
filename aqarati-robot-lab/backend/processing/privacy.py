"""Remove direct contact identifiers before any cloud-bound request."""

from __future__ import annotations

import re

PHONE_MARKER = "[رقم هاتف محجوب]"
ACCOUNT_MARKER = "[حساب محجوب]"
URL_MARKER = "[رابط حساب محجوب]"

_DIGITS = "0-9٠-٩۰-۹"
_PHONE_CANDIDATE = re.compile(
    rf"(?<![{_DIGITS}])\+?(?:[{_DIGITS}][\s().-]*){{9,15}}[{_DIGITS}](?![{_DIGITS}])"
)
_DIGIT_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_SOCIAL_URL = re.compile(
    r"(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.com|fb\.me|m\.me)/[^\s<>()]+",
    re.IGNORECASE,
)
_SOCIAL_LABEL = re.compile(
    r"(?im)(?:اسم\s+(?:الحساب|المستخدم)|حساب\s+(?:الفيس(?:بوك)?|facebook)|facebook\s*(?:name|id)?|فيس(?:بوك)?)"
    r"\s*[:：\-]\s*[^\n،,;؛]{2,80}"
)
_HANDLE = re.compile(r"(?<![\w@])@[A-Za-z0-9_.-]{3,64}")
_LABELED_ID = re.compile(
    rf"(?i)(?:facebook|fb|فيسبوك|معرف\s*الحساب)\s*(?:id)?\s*[:#-]?\s*[{_DIGITS}]{{5,25}}"
)


def redact_personal_data(text: str) -> str:
    """Return a deterministic redacted copy; the input is never mutated or logged."""
    redacted = _SOCIAL_URL.sub(URL_MARKER, text)
    redacted = _SOCIAL_LABEL.sub(ACCOUNT_MARKER, redacted)
    redacted = _LABELED_ID.sub(ACCOUNT_MARKER, redacted)
    redacted = _HANDLE.sub(ACCOUNT_MARKER, redacted)
    def replace_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0).translate(_DIGIT_TRANSLATION))
        local = digits
        if local.startswith("00964"):
            local = local[5:]
        elif local.startswith("964"):
            local = local[3:]
        if not local.startswith("0"):
            local = "0" + local
        return PHONE_MARKER if re.fullmatch(r"07[3-9]\d{8}", local) else match.group(0)

    redacted = _PHONE_CANDIDATE.sub(replace_phone, redacted)
    return redacted


def redact_secrets(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Sanitize bounded provider diagnostics before local persistence."""
    clean = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [محجوب]", text)
    for secret in secrets:
        if secret:
            clean = clean.replace(secret, "[سر محجوب]")
    return redact_personal_data(clean)
