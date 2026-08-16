"""FR-09b/10 member-7 approvals and reports router (risk acceptance slice)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.approvals_reports.application.services import (
    ApprovalsReportsServices,
    RiskAcceptanceService,
)
from biaice.modules.approvals_reports.domain.models import RiskAcceptance


router = APIRouter(prefix="/api/v1", tags=["approvals-reports"])


def get_approvals_reports_services(request: Request) -> ApprovalsReportsServices:
    services = getattr(request.app.state, "approvals_reports_services", None)
    if services is None:
        from biaice.core.errors import BiaiceError

        raise BiaiceError(
            "INTERNAL_ERROR",
            detail="Approvals/reports services are not configured on app.state.",
        )
    return services


def get_risk_acceptance_service(request: Request) -> RiskAcceptanceService:
    return get_approvals_reports_services(request).risk_acceptance


class CreateRiskAcceptanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: str = Field(min_length=1, max_length=200)
    metric: str = Field(min_length=1, max_length=200)
    acceptance_scope: str = Field(min_length=1, max_length=400)
    rationale: str = Field(min_length=1, max_length=2000)
    independent_approver_id: UUID
    valid_from: datetime
    valid_until: datetime


class RevokeRiskAcceptanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revocation_reason: str = Field(min_length=1, max_length=1000)


class RiskAcceptanceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[RiskAcceptance, ...]


@router.post(
    "/decision-units/{unit_id}/risk-acceptances",
    operation_id="create_risk_acceptance",
    response_model=RiskAcceptance,
    responses=PROBLEM_RESPONSES,
)
def create_risk_acceptance(
    body: CreateRiskAcceptanceRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.APPROVALS_RISK_CREATE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: RiskAcceptanceService = Depends(get_risk_acceptance_service),
) -> RiskAcceptance:
    del idempotency_key
    return service.create(
        identity=identity,
        decision_unit_id=unit_id,
        risk=body.risk,
        metric=body.metric,
        acceptance_scope=body.acceptance_scope,
        rationale=body.rationale,
        independent_approver_id=body.independent_approver_id,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/risk-acceptances",
    operation_id="list_risk_acceptances",
    response_model=RiskAcceptanceListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_risk_acceptances(
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.APPROVALS_RISK_READ)
    ),
    service: RiskAcceptanceService = Depends(get_risk_acceptance_service),
) -> RiskAcceptanceListResponse:
    return RiskAcceptanceListResponse(
        items=service.list(identity=identity, decision_unit_id=unit_id)
    )


@router.get(
    "/risk-acceptances/{risk_acceptance_id}",
    operation_id="get_risk_acceptance",
    response_model=RiskAcceptance,
    responses=PROBLEM_RESPONSES,
)
def get_risk_acceptance(
    risk_acceptance_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.APPROVALS_RISK_READ)
    ),
    service: RiskAcceptanceService = Depends(get_risk_acceptance_service),
) -> RiskAcceptance:
    return service.get(identity=identity, risk_acceptance_id=risk_acceptance_id)


@router.post(
    "/risk-acceptances/{risk_acceptance_id}/revoke",
    operation_id="revoke_risk_acceptance",
    response_model=RiskAcceptance,
    responses=PROBLEM_RESPONSES,
)
def revoke_risk_acceptance(
    body: RevokeRiskAcceptanceRequest,
    request: Request,
    risk_acceptance_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.APPROVALS_RISK_REVOKE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: RiskAcceptanceService = Depends(get_risk_acceptance_service),
) -> RiskAcceptance:
    del idempotency_key
    return service.revoke(
        identity=identity,
        risk_acceptance_id=risk_acceptance_id,
        revocation_reason=body.revocation_reason,
        request_id=request.state.request_id,
    )

