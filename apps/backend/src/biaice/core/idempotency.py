"""Idempotency-Key validation and durable repository port."""

from __future__ import annotations

import re
from typing import Annotated, Protocol

from fastapi import Header

from biaice.core.auth import TenantScope
from biaice.core.errors import BiaiceError

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")


def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if idempotency_key is None:
        raise BiaiceError("IDEMPOTENCY_KEY_REQUIRED")
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
        raise BiaiceError("INVALID_IDEMPOTENCY_KEY")
    return idempotency_key


IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=128)]


class IdempotencyRepository(Protocol):
    def reserve(self, *, scope: TenantScope, key: str, request_hash: str) -> bool: ...

    def record_response(
        self,
        *,
        scope: TenantScope,
        key: str,
        request_hash: str,
        status: int,
        body_hash: str,
    ) -> None: ...
