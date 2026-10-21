"""Optional local OCR with bounded image loading and SSRF protections."""

from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import httpx

from . import paths

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class OCRFailure(RuntimeError):
    def __init__(self, kind: str, message: str): super().__init__(message); self.kind = kind


class OCREngine(Protocol):
    name: str
    def extract(self, image: bytes, languages: str) -> str: ...


def image_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP": return "image/webp"
    return None


def _public_host(hostname: str) -> bool:
    try: infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror: return False
    if not infos: return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global: return False
    return True


def download_image(url: str, timeout_seconds: int = 10) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise OCRFailure("unsafe_url", "رابط الصورة غير آمن")
    if not _public_host(parsed.hostname):
        raise OCRFailure("private_network_blocked", "عناوين الشبكة الداخلية والمحلية محظورة")
    try:
        with httpx.Client(timeout=min(timeout_seconds, 15), follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", url, headers={"Accept": "image/jpeg,image/png,image/webp"}) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in ALLOWED_CONTENT_TYPES: raise OCRFailure("invalid_content_type", "نوع الصورة غير مدعوم")
                length = response.headers.get("content-length")
                if length and int(length) > MAX_IMAGE_BYTES: raise OCRFailure("image_too_large", "حجم الصورة يتجاوز 5MB")
                chunks = []; size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES: raise OCRFailure("image_too_large", "حجم الصورة يتجاوز 5MB")
                    chunks.append(chunk)
    except OCRFailure: raise
    except (httpx.HTTPError, ValueError) as exc: raise OCRFailure("download_failed", "تعذر تنزيل الصورة") from exc
    data = b"".join(chunks)
    if image_type(data) != content_type: raise OCRFailure("type_mismatch", "محتوى الصورة لا يطابق نوعها")
    return data


def read_local_image(relative_path: str) -> bytes:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts: raise OCRFailure("unsafe_path", "مسار الصورة يجب أن يكون نسبياً داخل data")
    candidate = paths.ensure_inside_project(paths.data_path(*relative.parts))
    if not paths.is_inside(candidate, paths.data_path()): raise OCRFailure("unsafe_path", "مسار الصورة خارج data")
    if not candidate.is_file(): raise OCRFailure("file_not_found", "ملف الصورة المحلي غير موجود")
    if candidate.stat().st_size > MAX_IMAGE_BYTES: raise OCRFailure("image_too_large", "حجم الصورة يتجاوز 5MB")
    data = candidate.read_bytes()
    if image_type(data) not in ALLOWED_CONTENT_TYPES: raise OCRFailure("invalid_content_type", "نوع الصورة غير مدعوم")
    return data


class TesseractEngine:
    name = "tesseract-local"

    def __init__(self):
        self.executable = shutil.which("tesseract")
        if not self.executable: raise OCRFailure("engine_unavailable", "Tesseract غير مثبت")

    def extract(self, image: bytes, languages: str) -> str:
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[image_type(image)]
        cache = paths.safe_write_path(paths.data_path("processed", "ocr-cache")); cache.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=cache, suffix=suffix, delete=False) as handle:
                handle.write(image); temp_path = Path(handle.name)
            result = subprocess.run(
                [self.executable, str(temp_path), "stdout", "-l", languages], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=60, check=False,
            )
            if result.returncode != 0: raise OCRFailure("ocr_failed", "فشل محرك OCR المحلي")
            return result.stdout.strip()
        except subprocess.TimeoutExpired as exc: raise OCRFailure("timeout", "انتهت مهلة OCR") from exc
        finally:
            if temp_path and temp_path.exists(): temp_path.unlink()


_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬", "01234567890123456789,")


def extract_suggestions(text: str) -> dict:
    normalized = text.translate(_ARABIC_DIGITS)
    suggestions: dict[str, object] = {}
    price = re.search(r"(?i)(?:السعر\s*[:\-]?\s*)?([0-9][0-9,\. ]{2,})\s*(دينار|دولار|IQD|USD)", normalized)
    if price:
        number = re.sub(r"[^0-9.]", "", price.group(1).replace(",", ""))
        try: suggestions.update(price=float(number), currency="IQD" if price.group(2).lower() in {"دينار", "iqd"} else "USD", price_text=price.group(0))
        except ValueError: pass
    area = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:م(?:تر)?(?:\s*مربع)?|م²)", normalized)
    if area: suggestions.update(area_sqm=float(area.group(1)), area_text=area.group(0))
    floor = re.search(r"(?:الطابق|طابق)\s*([0-9]+|الأرضي|ارضي)", normalized)
    if floor: suggestions["floor"] = floor.group(1)
    return suggestions
