from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from biaice.api.dependencies import get_audit_writer, get_gate_service
from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.idempotency import require_idempotency_key
from biaice.core.security.gates import GateAssessment, GateName, GateService

router = APIRouter(prefix="/api/v1", tags=["stage-gates"])


class GateListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[GateAssessment, ...]
    next_cursor: str | None = None


class GateAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason_code: str = Field(min_length=3, max_length=120)


class GateWaiverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason_code: str = Field(min_length=3, max_length=120)
    compensation_control: str = Field(min_length=3, max_length=500)
    expires_at: datetime


class ManualOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_type: str
    target_id: UUID
    reason_code: str
    before_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    after_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: datetime


@router.get(
    "/stage-gates",
    operation_id="list_stage_gates",
    response_model=GateListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_stage_gates(
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_READ)),
    gates: GateService = Depends(get_gate_service),
) -> GateListResponse:
    del identity
    return GateListResponse(items=tuple(gates.current(name) for name in GateName))


@router.get(
    "/stage-gates/{gate_name}",
    operation_id="get_stage_gate",
    response_model=GateAssessment,
    responses=PROBLEM_RESPONSES,
)
def get_stage_gate(
    gate_name: GateName,
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_READ)),
    gates: GateService = Depends(get_gate_service),
) -> GateAssessment:
    del identity
    return gates.current(gate_name)


@router.post(
    "/stage-gates/{gate_name}/assess",
    operation_id="assess_stage_gate",
    response_model=GateAssessment,
    responses=PROBLEM_RESPONSES,
)
def assess_stage_gate(
    gate_name: GateName,
    body: GateAssessmentRequest,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_ASSESS, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    audit: AuditWriter = Depends(get_audit_writer),
) -> GateAssessment:
    del gate_name, body, identity, idempotency_key
    require_audit(audit)
    # A client cannot self-attest PASS. Infrastructure will inject a signed,
    # machine evidence assessor in the secure profile.
    raise BiaiceError(
        "GATE_EVIDENCE_VERIFIER_UNAVAILABLE",
        detail=f"No machine verifier is bound (request {request.state.request_id}).",
    )


@router.post(
    "/stage-gates/{gate_name}/waivers/request",
    operation_id="request_stage_gate_waiver",
    responses=PROBLEM_RESPONSES,
)
def request_stage_gate_waiver(
    gate_name: GateName,
    body: GateWaiverRequest,
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_WAIVER_REQUEST, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
) -> None:
    del gate_name, body, identity, idempotency_key
    raise BiaiceError("WAIVER_PROHIBITED")


@router.post(
    "/stage-gates/{gate_name}/waivers/decide",
    operation_id="decide_stage_gate_waiver",
    responses=PROBLEM_RESPONSES,
)
def decide_stage_gate_waiver(
    gate_name: GateName,
    body: GateWaiverRequest,
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_WAIVER_DECIDE, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
) -> None:
    del gate_name, body, identity, idempotency_key
    raise BiaiceError("WAIVER_PROHIBITED")


@router.post(
    "/stage-gates/{gate_name}/waivers/expire",
    operation_id="expire_stage_gate_waiver",
    responses=PROBLEM_RESPONSES,
)
def expire_stage_gate_waiver(
    gate_name: GateName,
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_WAIVER_DECIDE, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
) -> None:
    del gate_name, identity, idempotency_key
    raise BiaiceError("WAIVER_PROHIBITED")


@router.get(
    "/manual-overrides",
    operation_id="list_manual_overrides",
    responses=PROBLEM_RESPONSES,
)
def list_manual_overrides(
    identity: IdentityContext = Depends(PermissionGuard(Permission.GATE_READ)),
) -> None:
    del identity
    raise BiaiceError("NOT_IMPLEMENTED", detail="Manual override storage is contract-only in M0.")


@router.post(
    "/manual-overrides",
    operation_id="append_manual_override",
    responses=PROBLEM_RESPONSES,
)
def append_manual_override(
    body: ManualOverrideRequest,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.MANUAL_OVERRIDE_APPEND, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
) -> None:
    del body, identity, idempotency_key
    raise BiaiceError(
        "NOT_IMPLEMENTED",
        detail="Manual overrides are append-only and not yet wired to PostgreSQL.",
    )


@router.post(
    "/manual-overrides/{override_id}/revoke",
    operation_id="revoke_manual_override",
    responses=PROBLEM_RESPONSES,
)
def revoke_manual_override(
    override_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.MANUAL_OVERRIDE_APPEND, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
) -> None:
    del override_id, identity, idempotency_key
    raise BiaiceError(
        "NOT_IMPLEMENTED",
        detail="Manual override revocation is an append-only event and is not wired in M0.",
    )
