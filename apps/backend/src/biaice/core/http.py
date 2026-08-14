"""ETag and signed cursor primitives used by all HTTP modules."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Header
from pydantic import BaseModel, ConfigDict

from biaice.core.auth import TenantScope
from biaice.core.errors import BiaiceError


def compute_etag(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")
    return f'"{hashlib.sha256(encoded).hexdigest()}"'


def require_if_match(
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> str:
    if if_match is None:
        raise BiaiceError("IF_MATCH_REQUIRED")
    if not (
        len(if_match) == 66
        and if_match.startswith('"')
        and if_match.endswith('"')
        and all(character in "0123456789abcdef" for character in if_match[1:-1])
    ):
        raise BiaiceError(
            "ETAG_MISMATCH", detail="If-Match must contain one strong SHA-256 ETag."
        )
    return if_match


def assert_etag(current_etag: str, supplied_etag: str) -> None:
    if not hmac.compare_digest(current_etag, supplied_etag):
        raise BiaiceError("ETAG_MISMATCH")


class CursorPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str
    data_domain_id: str
    sort_key: str
    tie_breaker: str
    expires_at: datetime


class CursorPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    next_cursor: str | None = None
    has_more: bool = False


class CursorCodec:
    def __init__(
        self, secret: bytes, *, ttl: timedelta = timedelta(minutes=15)
    ) -> None:
        if len(secret) < 32:
            raise ValueError("cursor HMAC secret must contain at least 32 bytes")
        self.secret = secret
        self.ttl = ttl

    @staticmethod
    def _b64encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
        if CursorCodec._b64encode(decoded) != value:
            raise ValueError("non-canonical base64url")
        return decoded

    def encode(self, *, scope: TenantScope, sort_key: str, tie_breaker: str) -> str:
        payload = CursorPayload(
            tenant_id=str(scope.tenant_id),
            data_domain_id=str(scope.data_domain_id),
            sort_key=sort_key,
            tie_breaker=tie_breaker,
            expires_at=datetime.now(timezone.utc) + self.ttl,
        )
        raw = payload.model_dump_json().encode("utf-8")
        signature = hmac.new(self.secret, raw, hashlib.sha256).digest()
        return f"{self._b64encode(raw)}.{self._b64encode(signature)}"

    def decode(self, cursor: str, *, scope: TenantScope) -> CursorPayload:
        try:
            raw_part, signature_part = cursor.split(".", 1)
            raw = self._b64decode(raw_part)
            supplied = self._b64decode(signature_part)
            expected = hmac.new(self.secret, raw, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, supplied):
                raise ValueError("bad signature")
            payload = CursorPayload.model_validate_json(raw)
            if payload.expires_at <= datetime.now(timezone.utc):
                raise ValueError("expired")
        except Exception as exc:
            raise BiaiceError("INVALID_CURSOR") from exc
        if payload.tenant_id != str(scope.tenant_id) or payload.data_domain_id != str(
            scope.data_domain_id
        ):
            raise BiaiceError("CURSOR_SCOPE_MISMATCH")
        return payload
