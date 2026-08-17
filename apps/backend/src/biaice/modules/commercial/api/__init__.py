"""FR-04 FastAPI router. Catalog typos (`commercial_policie`) are preserved."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.idempotency import require_idempotency_key
from biaice.core.money import Money
from biaice.modules.commercial.application.services import (
    CommercialService,
    CommercialServices,
)
from biaice.modules.commercial.domain.models import (
    CommercialPolicy,
    CostBaseline,
    StrategyReadinessAssessment,
    TaxMode,
)

router = APIRouter(prefix="/api/v1", tags=["commercial"])


def get_services(request: Request) -> CommercialServices:
    services = getattr(request.app.state, "commercial_services", None)
    if services is None:
        raise BiaiceError("INTERNAL_ERROR", detail="Commercial services are not configured.")
    return services


def get_service(request: Request) -> CommercialService:
    return get_services(request).commercial


class CostListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CostBaseline, ...]


class PolicyListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CommercialPolicy, ...]


class ReadinessListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[StrategyReadinessAssessment, ...]


class CreateCostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    tax_mode: TaxMode
    input_vat: Money
    cycle: str = Field(min_length=1, max_length=40)
    delivery_cost: Money
    post_award_cost: Money
    bid_preparation_cost: Money
    cashflow_in: Money
    cashflow_out: Money


class CreatePolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profit_floor: str = Field(min_length=1, max_length=40)
    cashflow_constraint: str = Field(min_length=1, max_length=200)
    capacity_constraint: str = Field(min_length=1, max_length=200)
    risk_threshold: str = Field(min_length=1, max_length=200)
    coverage_ratio: str = Field(min_length=1, max_length=40)
    min_award_quality: str = Field(min_length=1, max_length=80)
    objective_weights: dict[str, str] = Field(default_factory=dict)
    merge_tolerance: str = Field(min_length=1, max_length=40)
    exception_authority: str = Field(min_length=1, max_length=200)


def _extras(permission: str) -> dict[str, Any]:
    return {
        "x-contract-only": False,
        "x-owner": "member-4",
        "x-fr": "FR-04",
        "x-required-permission": permission,
        "x-schema-status": "OWNER_FROZEN",
    }


@router.get(
    "/decision-units/{unit_id}/cost-baselines",
    operation_id="list_cost_baselines",
    response_model=CostListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("fr-04:read"),
)
def list_cost_baselines(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_READ)),
    service: CommercialService = Depends(get_service),
) -> CostListResponse:
    return CostListResponse(items=service.list_cost_baselines(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/cost-baselines",
    operation_id="create_cost_baseline",
    response_model=CostBaseline,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("fr-04:create"), "x-idempotency-required": True},
)
def create_cost_baseline(
    body: CreateCostRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CommercialService = Depends(get_service),
) -> CostBaseline:
    del idempotency_key
    return service.create_cost_baseline(
        identity=identity,
        decision_unit_id=unit_id,
        currency=body.currency,
        tax_mode=body.tax_mode,
        input_vat=body.input_vat,
        cycle=body.cycle,
        delivery_cost=body.delivery_cost,
        post_award_cost=body.post_award_cost,
        bid_preparation_cost=body.bid_preparation_cost,
        cashflow_in=body.cashflow_in,
        cashflow_out=body.cashflow_out,
        request_id=request.state.request_id,
    )


@router.get(
    "/cost-baselines/{cost_baseline_id}",
    operation_id="get_cost_baseline",
    response_model=CostBaseline,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("fr-04:read"),
)
def get_cost_baseline(
    cost_baseline_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_READ)),
    service: CommercialService = Depends(get_service),
) -> CostBaseline:
    return service.get_cost_baseline(identity=identity, cost_baseline_id=cost_baseline_id)


@router.post(
    "/cost-baselines/{cost_baseline_id}/approve",
    operation_id="approve_cost_baseline",
    response_model=CostBaseline,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("fr-04:approve"), "x-idempotency-required": True},
)
def approve_cost_baseline(
    request: Request,
    cost_baseline_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_APPROVE, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CommercialService = Depends(get_service),
) -> CostBaseline:
    del idempotency_key
    return service.approve_cost_baseline(
        identity=identity,
        cost_baseline_id=cost_baseline_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/cost-baselines/{cost_baseline_id}/publish",
    operation_id="publish_cost_baseline",
    response_model=CostBaseline,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("fr-04:publish"), "x-idempotency-required": True},
)
def publish_cost_baseline(
    request: Request,
    cost_baseline_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_PUBLISH, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CommercialService = Depends(get_service),
) -> CostBaseline:
    del idempotency_key
    return service.publish_cost_baseline(
        identity=identity,
        cost_baseline_id=cost_baseline_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/commercial-policies",
    operation_id="list_commercial_policies",
    response_model=PolicyListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("fr-04:read"),
)
def list_commercial_policies(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_READ)),
    service: CommercialService = Depends(get_service),
) -> PolicyListResponse:
    return PolicyListResponse(items=service.list_policies(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/commercial-policies",
    operation_id="create_commercial_policie",
    response_model=CommercialPolicy,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("fr-04:create"), "x-idempotency-required": True},
)
def create_commercial_policie(
    body: CreatePolicyRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CommercialService = Depends(get_service),
) -> CommercialPolicy:
    del idempotency_key
    return service.create_policy(
        identity=identity,
        decision_unit_id=unit_id,
        profit_floor=body.profit_floor,
        cashflow_constraint=body.cashflow_constraint,
        capacity_constraint=body.capacity_constraint,
        risk_threshold=body.risk_threshold,
        coverage_ratio=body.coverage_ratio,
        min_award_quality=body.min_award_quality,
        objective_weights=body.objective_weights,
        merge_tolerance=body.merge_tolerance,
        exception_authority=body.exception_authority,
        request_id=request.state.request_id,
    )


@router.get(
    "/commercial-policies/{commercial_policie_id}",
    operation_id="get_commercial_policie",
    response_model=CommercialPolicy,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("fr-04:read"),
)
def get_commercial_policie(
    commercial_policie_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_READ)),
    service: CommercialService = Depends(get_service),
) -> CommercialPolicy:
    return service.get_policy(identity=identity, policy_id=commercial_policie_id)


@router.post(
    "/commercial-policies/{commercial_policy_id}/publish",
    operation_id="publish_commercial_policy",
    response_model=CommercialPolicy,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("fr-04:publish"), "x-idempotency-required": True},
)
def publish_commercial_policy(
    request: Request,
    commercial_policy_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_PUBLISH, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CommercialService = Depends(get_service),
) -> CommercialPolicy:
    del idempotency_key
    return service.publish_policy(
        identity=identity, policy_id=commercial_policy_id, request_id=request.state.request_id
    )


@router.get(
    "/decision-units/{unit_id}/readiness-assessments",
    operation_id="list_readiness_assessments",
    response_model=ReadinessListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("fr-04:read"),
)
def list_readiness_assessments(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_READ)),
    service: CommercialService = Depends(get_service),
) -> ReadinessListResponse:
    return ReadinessListResponse(items=service.list_readiness(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/readiness-assessments",
    operation_id="create_readiness_assessment",
    response_model=StrategyReadinessAssessment,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("fr-04:create"), "x-idempotency-required": True},
)
def create_readiness_assessment(
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CommercialService = Depends(get_service),
) -> StrategyReadinessAssessment:
    del idempotency_key
    return service.create_readiness(
        identity=identity, decision_unit_id=unit_id, request_id=request.state.request_id
    )


@router.get(
    "/readiness-assessments/{readiness_assessment_id}",
    operation_id="get_readiness_assessment",
    response_model=StrategyReadinessAssessment,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("fr-04:read"),
)
def get_readiness_assessment(
    readiness_assessment_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR04_READ)),
    service: CommercialService = Depends(get_service),
) -> StrategyReadinessAssessment:
    return service.get_readiness(identity=identity, readiness_id=readiness_assessment_id)
