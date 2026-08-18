"""Create stable member-4 domain errors from the platform catalog."""

from __future__ import annotations

from biaice.core.errors import BiaiceError


def m4_error(code: str, *, detail: str | None = None) -> BiaiceError:
    return BiaiceError(code, detail=detail)
