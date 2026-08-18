# Part 1: imports, router, helpers
"""FR-06/07/08/09a real implementation of the simulation router.

Registered before contract_stubs so FastAPI first-match-wins routes member-6 operations here.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.simulation.application.repository import InMemorySimulationRepository
from biaice.modules.simulation.application.services import (
    BaselineService,
    EligibilityService,
    OptimizationService,
    ScenarioSetService,
    SearchSpaceService,
    SimulationBatchService,
    SimulationServices,
    SnapshotService,
)
from biaice.modules.simulation.domain.eligibility import GateInputs
from biaice.modules.simulation.domain.models import (
    AwardMode,
    CandidateSearchSpace,
    DecimalStr,
    DecisionBaseline,
    ManifestItem,
    MergeAssessment,
    ObjectiveKind,
    OptimizationRun,
    RecommendationEligibility,
    ReviewValidity,
    ScenarioKind,
    ScenarioOutcome,
    ScenarioSet,
    ScenarioSetMember,
    ScenarioStrategyAssessment,
    SimulationAssessmentSnapshot,
    SimulationBatch,
    SimulationCandidate,
    StaticCandidateValidation,
    StrategyPlan,
    StressAxis,
    StressTestAssessment,
)
from biaice.modules.simulation.domain.optimization import CandidateBlueprint
from biaice.modules.simulation.domain.stress import StressScenario

router = APIRouter(prefix="/api/v1", tags=["simulation"])


def get_simulation_repository(request: Request) -> InMemorySimulationRepository:
    repository = getattr(request.app.state, "simulation_repository", None)
    if repository is None:
        raise BiaiceError(
            "INTERNAL_ERROR",
            detail=(
                "仿真仓储未配置 / Simulation repository is not configured on app.state."
            ),
        )
    return repository


def get_simulation_services(request: Request) -> SimulationServices:
    services = getattr(request.app.state, "simulation_services", None)
    if services is None:
        raise BiaiceError(
            "INTERNAL_ERROR",
            detail=(
                "仿真服务未配置 / Simulation services are not configured on app.state."
            ),
        )
    return services


def get_baseline_service(request: Request) -> BaselineService:
    return get_simulation_services(request).baseline


def get_search_space_service(request: Request) -> SearchSpaceService:
    return get_simulation_services(request).search_space


def get_scenario_set_service(request: Request) -> ScenarioSetService:
    return get_simulation_services(request).scenario_set


def get_batch_service(request: Request) -> SimulationBatchService:
    return get_simulation_services(request).batch


def get_optimization_service(request: Request) -> OptimizationService:
    return get_simulation_services(request).optimization


def get_eligibility_service(request: Request) -> EligibilityService:
    return get_simulation_services(request).eligibility


def get_snapshot_service(request: Request) -> SnapshotService:
    return get_simulation_services(request).snapshot
# Request bodies
class ManifestItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: UUID
    upstream_type: str = Field(min_length=1)
    upstream_id: UUID
    upstream_version_id: UUID
    upstream_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    dependency_type: str = Field(min_length=1)
    recorded_at: datetime

    @field_validator("recorded_at", mode="before")
    @classmethod
    def _recorded_at_must_be_iso(cls, value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("recorded_at must be ISO 8601 string") from exc
        raise ValueError("recorded_at must be ISO 8601 string, not " + type(value).__name__)

class FreezeBaselineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_unit_id: UUID
    manifest_items: tuple[ManifestItemRequest, ...] = Field(min_length=1)

class CreateSearchSpaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_unit_id: UUID
    baseline_id: UUID
    description: str = Field(min_length=1, max_length=400)
    dimension_axes: tuple[str, ...] = Field(min_length=1)
    candidate_count_lower_bound: int = Field(ge=1)

class ScenarioSetMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: UUID
    scenario_kind: str
    weight: str = Field(pattern=r"^-?\d+(\.\d+)?$")
    label: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] = Field(default_factory=dict)

class CreateScenarioSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_unit_id: UUID
    baseline_id: UUID
    search_space_id: UUID
    evaluation_space_id: UUID | None = None
    members: tuple[ScenarioSetMemberRequest, ...] = Field(min_length=1)
    stress_axes: tuple[str, ...] = Field(default_factory=tuple)

class CreateBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_unit_id: UUID
    baseline_id: UUID
    scenario_set_id: UUID
    award_mode: AwardMode
    policy_threshold: str = Field(pattern=r"^-?\d+(\.\d+)?$")

class CandidateBlueprintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    expected_cost: str = Field(pattern=r"^-?\d+(\.\d+)?$")
    expected_margin: str = Field(pattern=r"^-?\d+(\.\d+)?$")

class StressScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    axis: StressAxis
    feasible: bool
    stress_weight: str = Field(pattern=r"^-?\d+(\.\d+)?$")
    detail: str = Field(min_length=1, max_length=400)

class CreateOptimizationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective_kind: ObjectiveKind
    award_mode: AwardMode
    policy_threshold: str = Field(pattern=r"^-?\d+(\.\d+)?$")
    blueprints: tuple[CandidateBlueprintRequest, ...] = Field(min_length=1)
    stress_axes: tuple[StressAxis, ...]
    stress_scenarios: tuple[StressScenarioRequest, ...] = Field(default_factory=tuple)

class RecommendationEligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline_id: UUID
    snapshot_id: UUID | None = None
    precheck: ReviewValidity
    readiness: ReviewValidity
    static_validation: ReviewValidity
    scenario_assessment: ReviewValidity
    condition: ReviewValidity
    risk_acceptance: ReviewValidity

class SnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: dict[str, Any]

# Response envelopes
class BaselineListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[DecisionBaseline, ...]

class SearchSpaceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CandidateSearchSpace, ...]

class ScenarioSetListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ScenarioSet, ...]

class BatchListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[SimulationBatch, ...]

class CandidateListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[SimulationCandidate, ...]

class StaticValidationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[StaticCandidateValidation, ...]

class OutcomeListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ScenarioOutcome, ...]

class AssessmentListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ScenarioStrategyAssessment, ...]

class OptimizationRunListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[OptimizationRun, ...]

class StressAssessmentListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[StressTestAssessment, ...]

class StrategyPlanListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[StrategyPlan, ...]

class MergeAssessmentListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[MergeAssessment, ...]

class EligibilityListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[RecommendationEligibility, ...]

class SnapshotListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[SimulationAssessmentSnapshot, ...]

class SnapshotDownloadResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    snapshot: SimulationAssessmentSnapshot

# Helpers
def _manifest_items_from_request(items):
    return tuple(
        ManifestItem(
            item_id=item.item_id,
            upstream_type=item.upstream_type,
            upstream_id=item.upstream_id,
            upstream_version_id=item.upstream_version_id,
            upstream_content_hash=item.upstream_content_hash,
            dependency_type=item.dependency_type,
            recorded_at=item.recorded_at,
        )
        for item in items
    )

def _scenario_members_from_request(members):
    result = []
    for item in members:
        try:
            kind = ScenarioKind(item.scenario_kind)
        except ValueError as exc:
            raise BiaiceError(
                "SCENARIO_SET_INVALID",
                detail="scenario_kind must be one of " + ", ".join(k.value for k in ScenarioKind) + f"; got {item.scenario_kind!r}.",
            ) from exc
        result.append(
            ScenarioSetMember(
                scenario_id=item.scenario_id,
                scenario_kind=kind,
                weight=DecimalStr.coerce(item.weight),
                label=item.label,
                params=dict(item.params),
            )
        )
    return tuple(result)

def _blueprints_from_request(items):
    return tuple(
        CandidateBlueprint(
            label=item.label,
            parameters=dict(item.parameters),
            expected_cost=Decimal(item.expected_cost),
            expected_margin=Decimal(item.expected_margin),
        )
        for item in items
    )

def _stress_scenarios_from_request(items, *, stress_axes):
    from collections import defaultdict
    bucket = defaultdict(list)
    for axis in stress_axes:
        bucket[axis] = []
    for item in items:
        bucket[item.axis].append(
            StressScenario(
                axis=item.axis,
                feasible=item.feasible,
                stress_weight=Decimal(item.stress_weight),
                detail=item.detail,
            )
        )
    return bucket
# ===== Baseline =====
@router.get(
    "/decision-units/{unit_id}/decision-baselines",
    operation_id="list_decision_baselines",
    response_model=BaselineListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_decision_baselines(
    unit_id: UUID = Path(...),
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BASELINE_READ)),
    service: BaselineService = Depends(get_baseline_service),
) -> BaselineListResponse:
    return BaselineListResponse(items=service.list(identity=identity, decision_unit_id=unit_id))

@router.post(
    "/decision-units/{unit_id}/decision-baselines/freeze",
    operation_id="freeze_decision_baseline",
    response_model=DecisionBaseline,
    responses=PROBLEM_RESPONSES,
)
def freeze_decision_baseline(
    body: FreezeBaselineRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BASELINE_FREEZE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: BaselineService = Depends(get_baseline_service),
) -> DecisionBaseline:
    if body.decision_unit_id != unit_id:
        raise BiaiceError("TENANT_SCOPE_VIOLATION")
    return service.freeze(
        identity=identity,
        decision_unit_id=unit_id,
        manifest_items=_manifest_items_from_request(body.manifest_items),
        request_id=request.state.request_id,
    )

@router.get(
    "/decision-baselines/{decision_baseline_id}",
    operation_id="get_decision_baseline",
    response_model=DecisionBaseline,
    responses=PROBLEM_RESPONSES,
)
def get_decision_baseline(
    decision_baseline_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BASELINE_READ)),
    service: BaselineService = Depends(get_baseline_service),
) -> DecisionBaseline:
    return service.get(identity=identity, baseline_id=decision_baseline_id)

# ===== Search space =====
@router.get(
    "/decision-units/{unit_id}/candidate-search-spaces",
    operation_id="list_candidate_search_spaces",
    response_model=SearchSpaceListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_candidate_search_spaces(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BASELINE_READ)),
    service: SearchSpaceService = Depends(get_search_space_service),
) -> SearchSpaceListResponse:
    return SearchSpaceListResponse(items=service.list(identity=identity, decision_unit_id=unit_id))

@router.post(
    "/decision-units/{unit_id}/candidate-search-spaces",
    operation_id="create_candidate_search_space",
    response_model=CandidateSearchSpace,
    responses=PROBLEM_RESPONSES,
)
def create_candidate_search_space(
    body: CreateSearchSpaceRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BASELINE_FREEZE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: SearchSpaceService = Depends(get_search_space_service),
) -> CandidateSearchSpace:
    if body.decision_unit_id != unit_id:
        raise BiaiceError("TENANT_SCOPE_VIOLATION")
    return service.create(
        identity=identity,
        decision_unit_id=unit_id,
        baseline_id=body.baseline_id,
        description=body.description,
        dimension_axes=list(body.dimension_axes),
        candidate_count_lower_bound=body.candidate_count_lower_bound,
        request_id=request.state.request_id,
    )

@router.get(
    "/candidate-search-spaces/{candidate_search_space_id}",
    operation_id="get_candidate_search_space",
    response_model=CandidateSearchSpace,
    responses=PROBLEM_RESPONSES,
)
def get_candidate_search_space(
    candidate_search_space_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BASELINE_READ)),
    service: SearchSpaceService = Depends(get_search_space_service),
) -> CandidateSearchSpace:
    return service.get(identity=identity, search_space_id=candidate_search_space_id)

# ===== Scenario set =====
@router.get(
    "/decision-units/{unit_id}/scenario-sets",
    operation_id="list_scenario_sets",
    response_model=ScenarioSetListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_scenario_sets(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BASELINE_READ)),
    service: ScenarioSetService = Depends(get_scenario_set_service),
) -> ScenarioSetListResponse:
    return ScenarioSetListResponse(items=service.list(identity=identity, decision_unit_id=unit_id))

@router.post(
    "/decision-units/{unit_id}/scenario-sets",
    operation_id="create_scenario_set",
    response_model=ScenarioSet,
    responses=PROBLEM_RESPONSES,
)
def create_scenario_set(
    body: CreateScenarioSetRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BASELINE_FREEZE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ScenarioSetService = Depends(get_scenario_set_service),
    repository: InMemorySimulationRepository = Depends(get_simulation_repository),
) -> ScenarioSet:
    if body.decision_unit_id != unit_id:
        raise BiaiceError("TENANT_SCOPE_VIOLATION")
    evaluation_space = repository.get_search_space(scope=identity.scope, search_space_id=body.evaluation_space_id) if body.evaluation_space_id else None
    return service.create(
        identity=identity,
        decision_unit_id=unit_id,
        baseline_id=body.baseline_id,
        search_space_id=body.search_space_id,
        evaluation_space_id=evaluation_space,
        members=_scenario_members_from_request(body.members),
        stress_axes=[StressAxis(axis) for axis in body.stress_axes],
        request_id=request.state.request_id,
    )

@router.get(
    "/scenario-sets/{scenario_set_id}",
    operation_id="get_scenario_set",
    response_model=ScenarioSet,
    responses=PROBLEM_RESPONSES,
)
def get_scenario_set(
    scenario_set_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BASELINE_READ)),
    service: ScenarioSetService = Depends(get_scenario_set_service),
) -> ScenarioSet:
    return service.get(identity=identity, scenario_set_id=scenario_set_id)

@router.post(
    "/scenario-sets/{scenario_set_id}/freeze",
    operation_id="freeze_scenario_set",
    response_model=ScenarioSet,
    responses=PROBLEM_RESPONSES,
)
def freeze_scenario_set(
    scenario_set_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BASELINE_FREEZE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ScenarioSetService = Depends(get_scenario_set_service),
) -> ScenarioSet:
    return service.freeze(
        identity=identity,
        scenario_set_id=scenario_set_id,
        request_id=request.state.request_id,
    )
# ===== Batches =====
@router.post(
    "/decision-units/{unit_id}/simulation-batches",
    operation_id="create_simulation_batch",
    response_model=SimulationBatch,
    responses=PROBLEM_RESPONSES,
)
def create_simulation_batch(
    body: CreateBatchRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BATCH_RUN, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: SimulationBatchService = Depends(get_batch_service),
) -> SimulationBatch:
    if body.decision_unit_id != unit_id:
        raise BiaiceError("TENANT_SCOPE_VIOLATION")
    return service.create(
        identity=identity,
        decision_unit_id=unit_id,
        baseline_id=body.baseline_id,
        scenario_set_id=body.scenario_set_id,
        award_mode=body.award_mode,
        policy_threshold=body.policy_threshold,
        request_id=request.state.request_id,
    )

@router.get(
    "/decision-units/{unit_id}/simulation-batches",
    operation_id="list_simulation_batches",
    response_model=BatchListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_simulation_batches(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: SimulationBatchService = Depends(get_batch_service),
) -> BatchListResponse:
    return BatchListResponse(items=service.list(identity=identity, decision_unit_id=unit_id))

@router.get(
    "/simulation-batches/{batch_id}",
    operation_id="get_simulation_batch",
    response_model=SimulationBatch,
    responses=PROBLEM_RESPONSES,
)
def get_simulation_batch(
    batch_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: SimulationBatchService = Depends(get_batch_service),
) -> SimulationBatch:
    return service.get(identity=identity, batch_id=batch_id)

@router.post(
    "/simulation-batches/{batch_id}/cancel",
    operation_id="cancel_simulation_batch",
    response_model=SimulationBatch,
    responses=PROBLEM_RESPONSES,
)
def cancel_simulation_batch(
    batch_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BATCH_RUN, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: SimulationBatchService = Depends(get_batch_service),
) -> SimulationBatch:
    return service.cancel(
        identity=identity,
        batch_id=batch_id,
        request_id=request.state.request_id,
    )

@router.post(
    "/simulation-batches/{batch_id}/retry",
    operation_id="retry_simulation_batch",
    response_model=SimulationBatch,
    responses=PROBLEM_RESPONSES,
)
def retry_simulation_batch(
    batch_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_BATCH_RUN, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: SimulationBatchService = Depends(get_batch_service),
) -> SimulationBatch:
    return service.retry(
        identity=identity,
        batch_id=batch_id,
        request_id=request.state.request_id,
    )

@router.get(
    "/simulation-batches/{batch_id}/candidates",
    operation_id="list_simulation_batch_candidates",
    response_model=CandidateListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_simulation_batch_candidates(
    batch_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    repository: InMemorySimulationRepository = Depends(get_simulation_repository),
) -> CandidateListResponse:
    return CandidateListResponse(items=repository.list_candidates(scope=identity.scope, batch_id=batch_id))

@router.get(
    "/simulation-batches/{batch_id}/static-validations",
    operation_id="list_simulation_batch_static_validations",
    response_model=StaticValidationListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_simulation_batch_static_validations(
    batch_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    repository: InMemorySimulationRepository = Depends(get_simulation_repository),
) -> StaticValidationListResponse:
    return StaticValidationListResponse(items=repository.list_static_validations(scope=identity.scope, batch_id=batch_id))

@router.get(
    "/simulation-batches/{batch_id}/scenario-outcomes",
    operation_id="list_simulation_batch_scenario_outcomes",
    response_model=OutcomeListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_simulation_batch_scenario_outcomes(
    batch_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    repository: InMemorySimulationRepository = Depends(get_simulation_repository),
) -> OutcomeListResponse:
    return OutcomeListResponse(items=repository.list_scenario_outcomes(scope=identity.scope, batch_id=batch_id))

@router.get(
    "/simulation-batches/{batch_id}/scenario-assessments",
    operation_id="list_simulation_batch_scenario_assessments",
    response_model=AssessmentListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_simulation_batch_scenario_assessments(
    batch_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    repository: InMemorySimulationRepository = Depends(get_simulation_repository),
) -> AssessmentListResponse:
    return AssessmentListResponse(items=repository.list_strategy_assessments(scope=identity.scope, batch_id=batch_id))
# ===== Optimization =====
@router.post(
    "/simulation-batches/{batch_id}/optimization-runs",
    operation_id="create_optimization_run",
    response_model=OptimizationRun,
    responses=PROBLEM_RESPONSES,
)
def create_optimization_run(
    body: CreateOptimizationRunRequest,
    request: Request,
    batch_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_OPTIMIZATION_RUN, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRun:
    return service.create_run(
        identity=identity,
        batch_id=batch_id,
        objective_kind=body.objective_kind,
        award_mode=body.award_mode,
        policy_threshold=body.policy_threshold,
        blueprints=_blueprints_from_request(body.blueprints),
        stress_axes=list(body.stress_axes),
        stress_scenarios=_stress_scenarios_from_request(body.stress_scenarios, stress_axes=body.stress_axes),
        request_id=request.state.request_id,
    )

@router.get(
    "/simulation-batches/{batch_id}/optimization-runs",
    operation_id="list_optimization_runs",
    response_model=OptimizationRunListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_optimization_runs(
    batch_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRunListResponse:
    return OptimizationRunListResponse(items=service.list(identity=identity, batch_id=batch_id))

@router.get(
    "/optimization-runs/{run_id}",
    operation_id="get_optimization_run",
    response_model=OptimizationRun,
    responses=PROBLEM_RESPONSES,
)
def get_optimization_run(
    run_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRun:
    return service.get(identity=identity, run_id=run_id)

@router.post(
    "/optimization-runs/{run_id}/finalize",
    operation_id="finalize_optimization_run",
    response_model=OptimizationRun,
    responses=PROBLEM_RESPONSES,
)
def finalize_optimization_run(
    run_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_PLAN_PUBLISH, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRun:
    return service.finalize(
        identity=identity,
        run_id=run_id,
        request_id=request.state.request_id,
    )

@router.post(
    "/optimization-runs/{run_id}/invalidate",
    operation_id="invalidate_optimization_run",
    response_model=OptimizationRun,
    responses=PROBLEM_RESPONSES,
)
def invalidate_optimization_run(
    run_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_PLAN_PUBLISH, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRun:
    return service.invalidate(
        identity=identity,
        run_id=run_id,
        request_id=request.state.request_id,
    )

@router.get(
    "/optimization-runs/{run_id}/stress-test-assessments",
    operation_id="list_optimization_stress_test_assessments",
    response_model=StressAssessmentListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_optimization_stress_test_assessments(
    run_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: OptimizationService = Depends(get_optimization_service),
) -> StressAssessmentListResponse:
    return StressAssessmentListResponse(items=service.list_stress(identity=identity, run_id=run_id))

@router.get(
    "/optimization-runs/{run_id}/strategy-plans",
    operation_id="list_optimization_strategy_plans",
    response_model=StrategyPlanListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_optimization_strategy_plans(
    run_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: OptimizationService = Depends(get_optimization_service),
) -> StrategyPlanListResponse:
    return StrategyPlanListResponse(items=service.list_plans(identity=identity, run_id=run_id))

@router.get(
    "/optimization-runs/{run_id}/merge-assessments",
    operation_id="list_optimization_merge_assessments",
    response_model=MergeAssessmentListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_optimization_merge_assessments(
    run_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_BATCH_READ)),
    service: OptimizationService = Depends(get_optimization_service),
) -> MergeAssessmentListResponse:
    return MergeAssessmentListResponse(items=service.list_merge_assessments(identity=identity, run_id=run_id))

@router.post(
    "/strategy-plans/{strategy_plan_id}/publish",
    operation_id="publish_strategy_plan",
    response_model=StrategyPlan,
    responses=PROBLEM_RESPONSES,
)
def publish_strategy_plan(
    strategy_plan_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_PLAN_PUBLISH, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: OptimizationService = Depends(get_optimization_service),
) -> StrategyPlan:
    return service.publish_plan(
        identity=identity,
        plan_id=strategy_plan_id,
        request_id=request.state.request_id,
    )

@router.post(
    "/strategy-plans/{strategy_plan_id}/invalidate",
    operation_id="invalidate_strategy_plan",
    response_model=StrategyPlan,
    responses=PROBLEM_RESPONSES,
)
def invalidate_strategy_plan(
    strategy_plan_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_PLAN_PUBLISH, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: OptimizationService = Depends(get_optimization_service),
) -> StrategyPlan:
    return service.invalidate_plan(
        identity=identity,
        plan_id=strategy_plan_id,
        request_id=request.state.request_id,
    )

# ===== Eligibility =====
@router.post(
    "/decision-units/{unit_id}/recommendation-eligibilities",
    operation_id="create_recommendation_eligibilitie",
    response_model=RecommendationEligibility,
    responses=PROBLEM_RESPONSES,
)
def create_recommendation_eligibility(
    body: RecommendationEligibilityRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_ELIGIBILITY_ASSESS, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EligibilityService = Depends(get_eligibility_service),
) -> RecommendationEligibility:
    return service.assess(
        identity=identity,
        decision_unit_id=unit_id,
        baseline_id=body.baseline_id,
        snapshot_id=body.snapshot_id,
        inputs=GateInputs(
            precheck=body.precheck,
            readiness=body.readiness,
            static_validation=body.static_validation,
            scenario_assessment=body.scenario_assessment,
            condition=body.condition,
            risk_acceptance=body.risk_acceptance,
        ),
        request_id=request.state.request_id,
    )

@router.get(
    "/decision-units/{unit_id}/recommendation-eligibilities",
    operation_id="list_recommendation_eligibilities",
    response_model=EligibilityListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_recommendation_eligibilities(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_AUDIT_READ)),
    service: EligibilityService = Depends(get_eligibility_service),
) -> EligibilityListResponse:
    return EligibilityListResponse(items=service.list(identity=identity, decision_unit_id=unit_id))

@router.get(
    "/recommendation-eligibilities/{recommendation_eligibilitie_id}",
    operation_id="get_recommendation_eligibilitie",
    response_model=RecommendationEligibility,
    responses=PROBLEM_RESPONSES,
)
def get_recommendation_eligibility(
    recommendation_eligibilitie_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_AUDIT_READ)),
    service: EligibilityService = Depends(get_eligibility_service),
) -> RecommendationEligibility:
    return service.get(identity=identity, eligibility_id=recommendation_eligibilitie_id)

# ===== Snapshots =====
@router.post(
    "/decision-units/{unit_id}/simulation-assessment-snapshots",
    operation_id="create_simulation_assessment_snapshot",
    response_model=SimulationAssessmentSnapshot,
    responses=PROBLEM_RESPONSES,
)
def create_simulation_assessment_snapshot(
    body: SnapshotRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.SIMULATION_SNAPSHOT_CREATE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: SnapshotService = Depends(get_snapshot_service),
) -> SimulationAssessmentSnapshot:
    return service.create(
        identity=identity,
        decision_unit_id=unit_id,
        payload=body.payload,
        request_id=request.state.request_id,
    )

@router.get(
    "/decision-units/{unit_id}/simulation-assessment-snapshots",
    operation_id="list_simulation_assessment_snapshots",
    response_model=SnapshotListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_simulation_assessment_snapshots(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_AUDIT_READ)),
    service: SnapshotService = Depends(get_snapshot_service),
) -> SnapshotListResponse:
    return SnapshotListResponse(items=service.list(identity=identity, decision_unit_id=unit_id))

@router.get(
    "/simulation-assessment-snapshots/{simulation_assessment_snapshot_id}",
    operation_id="get_simulation_assessment_snapshot",
    response_model=SimulationAssessmentSnapshot,
    responses=PROBLEM_RESPONSES,
)
def get_simulation_assessment_snapshot(
    simulation_assessment_snapshot_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_AUDIT_READ)),
    service: SnapshotService = Depends(get_snapshot_service),
) -> SimulationAssessmentSnapshot:
    return service.get(identity=identity, snapshot_id=simulation_assessment_snapshot_id)

@router.get(
    "/simulation-assessment-snapshots/{simulation_assessment_snapshot_id}/download",
    operation_id="download_simulation_assessment_snapshot",
    response_model=SnapshotDownloadResponse,
    responses=PROBLEM_RESPONSES,
)
def download_simulation_assessment_snapshot(
    simulation_assessment_snapshot_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.SIMULATION_AUDIT_READ)),
    service: SnapshotService = Depends(get_snapshot_service),
) -> SnapshotDownloadResponse:
    snapshot = service.download(identity=identity, snapshot_id=simulation_assessment_snapshot_id)
    return SnapshotDownloadResponse(snapshot=snapshot)
