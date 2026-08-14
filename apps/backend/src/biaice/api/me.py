from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES

router = APIRouter(prefix="/api/v1", tags=["identity"])


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    subject_id: UUID
    username: str
    display_name: str | None
    tenant_id: UUID
    data_domain_id: UUID
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    mfa_verified: bool
    authenticated_at: datetime


@router.get(
    "/me",
    operation_id="get_current_user",
    response_model=MeResponse,
    responses=PROBLEM_RESPONSES,
)
def get_me(
    identity: IdentityContext = Depends(PermissionGuard(Permission.PROFILE_READ)),
) -> MeResponse:
    return MeResponse(
        subject_id=identity.subject_id,
        username=identity.username,
        display_name=identity.display_name,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        roles=tuple(sorted(role.value for role in identity.roles)),
        permissions=tuple(
            sorted(permission.value for permission in identity.permissions)
        ),
        mfa_verified=identity.mfa_verified,
        authenticated_at=identity.authenticated_at,
    )
