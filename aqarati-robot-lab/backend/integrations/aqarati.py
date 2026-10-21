"""Draft-only Aqarati connector based on the documented Robot API contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx


def validate_base_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Aqarati base URL must be a credential-free HTTPS origin")
    return value.rstrip("/")


@dataclass(frozen=True)
class SyncResponse:
    remote_draft_id: str
    http_status: int


class AqaratiFailure(RuntimeError):
    def __init__(self, kind: str, message: str, http_status: int | None = None):
        super().__init__(message); self.kind = kind; self.http_status = http_status


class AqaratiConnector(Protocol):
    def capabilities(self) -> dict: ...
    def create_draft(self, payload: dict, idempotency_key: str) -> SyncResponse: ...


class HttpAqaratiConnector:
    def __init__(self, base_url: str, draft_path: str, service_identity: str, token: str, timeout: int = 15):
        self.base_url = validate_base_url(base_url)
        if not draft_path.startswith("/") or ".." in draft_path: raise ValueError("invalid draft path")
        if not token: raise ValueError("AQARATI_SERVICE_TOKEN is required")
        self.draft_path = draft_path; self.identity = service_identity; self.token = token; self.timeout = timeout

    def _headers(self, idempotency_key: str | None = None):
        result = {"Authorization": "Bearer " + self.token, "X-Service-Identity": self.identity, "Accept": "application/json"}
        if idempotency_key: result["Idempotency-Key"] = idempotency_key
        return result

    def capabilities(self) -> dict:
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False, trust_env=False) as client:
                response = client.get(self.base_url + "/api/robot/capabilities", headers=self._headers())
        except httpx.HTTPError as exc: raise AqaratiFailure("connection_error", "تعذر الاتصال بـAqarati") from exc
        if response.status_code != 200: raise AqaratiFailure("permission_failed", f"Aqarati returned HTTP {response.status_code}", response.status_code)
        data = response.json()
        if not data.get("can_create_drafts") or data.get("can_publish") is True:
            raise AqaratiFailure("unsafe_permissions", "هوية الخدمة يجب أن تنشئ مسودات فقط")
        return data

    def create_draft(self, payload: dict, idempotency_key: str) -> SyncResponse:
        if payload.get("publish") is not False or payload.get("lifecycle") != "draft":
            raise AqaratiFailure("unsafe_payload", "public publishing is forbidden")
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False, trust_env=False) as client:
                response = client.post(self.base_url + self.draft_path, headers=self._headers(idempotency_key), json=payload)
        except httpx.TimeoutException as exc: raise AqaratiFailure("timeout", "انتهت مهلة إرسال المسودة") from exc
        except httpx.HTTPError as exc: raise AqaratiFailure("connection_error", "تعذر إرسال المسودة") from exc
        if response.status_code not in {200, 201}: raise AqaratiFailure("http_error", f"Aqarati returned HTTP {response.status_code}", response.status_code)
        try: remote_id = str(response.json()["draft_id"])
        except (ValueError, KeyError) as exc: raise AqaratiFailure("invalid_response", "استجابة Aqarati لا تحتوي draft_id", response.status_code) from exc
        return SyncResponse(remote_draft_id=remote_id, http_status=response.status_code)
