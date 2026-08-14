"""Internal network endpoints that must remain fail-closed until adapters exist."""

from __future__ import annotations

from fastapi import APIRouter

from biaice.core.errors import BiaiceError

router = APIRouter(prefix="/internal", include_in_schema=False)


@router.post("/provider-egress/authorize")
def authorize_provider_egress() -> None:
    """Deny every grant until member 5 binds an atomic single-use grant store.

    The handler intentionally declares no request model, so FastAPI does not
    parse or retain the opaque grant while the authorization capability is
    unavailable. Network placement is defense in depth, never authorization.
    """

    raise BiaiceError("EGRESS_AUTHORIZATION_UNAVAILABLE")
