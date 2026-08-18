"""Application services for FR-06/07/08/09a simulation.

Each service:
    * owns one aggregate family (baseline, search-space, scenario-set, batch,
      optimization, eligibility, snapshot);
    * takes the in-memory repository + clock + audit + outbox + job port as
      injected dependencies (composition root in :func:`configure_simulation`);
    * writes a single immutable Pydantic model, then publishes an
      :class:`AuditEvent` and (when relevant) an :class:`OutboxEventRecord`
      and (when relevant) dispatches a :class:`JobRecord` for the worker.

The service signatures are deterministic; the API layer wraps them into
HTTP handlers. Error semantics are inherited from the domain helpers: any
violation produces a :class:`BiaiceError` whose `code` matches the M0
catalog.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.modules.simulation.application.repository import InMemorySimulationRepository
from biaice.modules.simulation.domain.eligibility import (
    GateInputs,
    assert_eligibility_for_recommendation,
    assess_eligibility,
)
from biaice.modules.simulation.domain.manifest import (
    assert_manifest_complete,
    assert_manifest_matches_versions,
    build_manifest,
)
from biaice.modules.simulation.domain.merge import (
    MergeRequest,
    assert_merge_accepted,
    merge_assessments,
)
from biaice.modules.simulation.domain.models import (
    AwardMode,
    BaselineState,
    BatchState,
    CandidateSearchSpace,
    DecimalStr,
    DecisionBaseline,
    ManifestItem,
    MergeAssessment,
    ObjectiveKind,
    OptimizationRun,
    OptimizationState,
    PlanState,
    RecommendationEligibility,
    ReviewValidity,
    ScenarioKind,
    ScenarioOutcome,
    ScenarioSet,
    ScenarioSetMember,
    ScenarioSetState,
    ScenarioStrategyAssessment,
    SearchSpaceState,
    SimulationAssessmentSnapshot,
    SimulationBatch,
    SimulationCandidate,
    SnapshotState,
    StaticValidationStatus,
    StrategyPlan,
    StressAxis,
    StressTestAssessment,
    new_uuid,
)
from biaice.modules.simulation.domain.optimization import (
    CandidateBlueprint,
    generate_candidates,
)
from biaice.modules.simulation.domain.referee import RefereeInput, evaluate_scenario
from biaice.modules.simulation.domain.scenarios import (
    freeze_scenarios,
    validate_search_eval_independence,
)
from biaice.modules.simulation.domain.snapshot import (
    SnapshotRequest,
    assert_shadow_watermark,
    create_snapshot,
)
from biaice.modules.simulation.domain.static_validation import (
    StaticValidationContext,
    StaticValidationResult,
    assert_validation_passed,
    validate_candidate,
)
from biaice.modules.simulation.domain.stress import (
    StressScenario,
    assert_no_stress_axis_in_probability,
    run_stress_tests,
)


class SimulationServices:
    """Composition root for the seven simulation services."""

    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port
        self.baseline = BaselineService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.search_space = SearchSpaceService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.scenario_set = ScenarioSetService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.batch = SimulationBatchService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.optimization = OptimizationService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.eligibility = EligibilityService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.snapshot = SnapshotService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )


def configure_simulation(
    app, *, repository: InMemorySimulationRepository | None = None
) -> SimulationServices:
    """Attach the simulation services to the FastAPI app state."""
    repository = repository or InMemorySimulationRepository()
    services = SimulationServices(
        repository=repository,
        clock=app.state.settings.__class__.clock()
        if hasattr(app.state.settings, "clock")
        else SystemClock(),
        audit_writer=app.state.audit_writer,
        outbox_port=getattr(app.state, "outbox_port", None),
    )
    app.state.simulation_repository = repository
    app.state.simulation_services = services
    return services


# ------------------------------------------------------------------ helpers
def _emit_event(
    outbox_port: OutboxPort | None,
    *,
    identity: IdentityContext,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: Mapping[str, Any],
    request_id: str,
) -> None:
    if outbox_port is None:
        return
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=identity.scope.project_ids.__iter__().__next__()
        if identity.scope.project_ids
        else None,
        decision_unit_id=identity.scope.decision_unit_ids.__iter__().__next__()
        if identity.scope.decision_unit_ids
        else None,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        occurred_at=datetime.now(timezone.utc),
        actor_id=identity.subject_id,
        request_id=request_id,
        correlation_id=uuid4(),
        causation_id=None,
        payload=dict(payload),
    )
    outbox_port.append(scope=identity.scope, event=envelope)


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ------------------------------------------------------------------ baseline
class BaselineService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def freeze(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        manifest_items: Sequence[ManifestItem],
        request_id: str,
        live_versions: Mapping[UUID, str] | None = None,
    ) -> DecisionBaseline:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        if not manifest_items:
            raise BiaiceError(
                "BASELINE_INCOMPLETE",
                detail=(
                    "决策基线 input manifest 不能为空 / Decision baseline manifest must "
                    "include at least one upstream reference."
                ),
            )
        manifest = build_manifest(list(manifest_items))
        baseline = DecisionBaseline(
            baseline_id=new_uuid(),
            version_id=new_uuid(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=identity.scope.project_ids.__iter__().__next__()
            if identity.scope.project_ids
            else None,
            decision_unit_id=decision_unit_id,
            manifest=manifest,
            state=BaselineState.FROZEN,
            frozen_at=self.clock.now(),
            frozen_by=identity.subject_id,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
        )
        if live_versions is not None:
            assert_manifest_matches_versions(baseline, live_versions)
        assert_manifest_complete(baseline)
        self.repository.upsert_baseline(baseline)
        self.audit_writer.write(
            identity=identity,
            action="simulation.baseline.freeze",
            object_type="DecisionBaseline",
            object_id=baseline.baseline_id,
            request_id=request_id,
            reason_code="BASELINE_FROZEN",
            outcome="ACCEPTED",
            object_version_id=baseline.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="simulation.decision_baseline_frozen.v1",
            aggregate_type="DecisionBaseline",
            aggregate_id=baseline.baseline_id,
            payload={
                "baseline_id": str(baseline.baseline_id),
                "version_id": str(baseline.version_id),
                "decision_unit_id": str(decision_unit_id),
                "manifest_hash": baseline.manifest.manifest_hash,
            },
            request_id=request_id,
        )
        return baseline

    def list(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[DecisionBaseline, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        return self.repository.list_baselines(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )

    def get(self, *, identity: IdentityContext, baseline_id: UUID) -> DecisionBaseline:
        baseline = self.repository.get_baseline(scope=identity.scope, baseline_id=baseline_id)
        if baseline is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(
                    f"决策基线不存在或不可见 / Decision baseline {baseline_id} not found in scope."
                ),
            )
        return baseline


# ------------------------------------------------------------------ search space
class SearchSpaceService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        baseline_id: UUID,
        description: str,
        dimension_axes: Sequence[str],
        candidate_count_lower_bound: int,
        request_id: str,
    ) -> CandidateSearchSpace:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        baseline = self.repository.get_baseline(scope=identity.scope, baseline_id=baseline_id)
        if baseline is None:
            raise BiaiceError(
                "BASELINE_INCOMPLETE",
                detail=(
                    "必须先冻结决策基线 / Decision baseline must be frozen before a "
                    "candidate search space can be created."
                ),
            )
        space = CandidateSearchSpace(
            search_space_id=new_uuid(),
            version_id=new_uuid(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=identity.scope.project_ids.__iter__().__next__()
            if identity.scope.project_ids
            else None,
            decision_unit_id=decision_unit_id,
            baseline_version_id=baseline.version_id,
            description=description,
            state=SearchSpaceState.FROZEN,
            dimension_axes=tuple(dimension_axes),
            candidate_count_lower_bound=candidate_count_lower_bound,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
            frozen_at=self.clock.now(),
            frozen_by=identity.subject_id,
        )
        self.repository.upsert_search_space(space)
        self.audit_writer.write(
            identity=identity,
            action="simulation.search_space.create",
            object_type="CandidateSearchSpace",
            object_id=space.search_space_id,
            request_id=request_id,
            reason_code="SEARCH_SPACE_FROZEN",
            outcome="ACCEPTED",
            object_version_id=space.version_id,
        )
        return space

    def list(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[CandidateSearchSpace, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        return self.repository.list_search_spaces(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )

    def get(self, *, identity: IdentityContext, search_space_id: UUID) -> CandidateSearchSpace:
        space = self.repository.get_search_space(
            scope=identity.scope, search_space_id=search_space_id
        )
        if space is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(
                    f"候选搜索空间不存在 / Candidate search space {search_space_id} not found in scope."
                ),
            )
        return space


# ------------------------------------------------------------------ scenario set
class ScenarioSetService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        baseline_id: UUID,
        search_space_id: UUID,
        evaluation_space_id: UUID | None,
        members: Sequence[ScenarioSetMember],
        stress_axes: Sequence[StressAxis],
        request_id: str,
    ) -> ScenarioSet:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        baseline = self.repository.get_baseline(scope=identity.scope, baseline_id=baseline_id)
        if baseline is None:
            raise BiaiceError(
                "BASELINE_INCOMPLETE",
                detail=(
                    "必须先冻结决策基线 / Decision baseline must be frozen before a "
                    "scenario set can be created."
                ),
            )
        space = self.repository.get_search_space(
            scope=identity.scope, search_space_id=search_space_id
        )
        if space is None or space.state != SearchSpaceState.FROZEN:
            raise BiaiceError(
                "SCENARIO_SET_INVALID",
                detail=(
                    "搜索空间必须先冻结 / Search space must be FROZEN before the scenario set."
                ),
            )
        evaluation_space_obj = None
        if evaluation_space_id is not None:
            evaluation_space_obj = self.repository.get_search_space(
                scope=identity.scope, search_space_id=evaluation_space_id
            )
        scenario_set = freeze_scenarios(
            set_id=new_uuid(),
            version_id=new_uuid(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=identity.scope.project_ids.__iter__().__next__()
            if identity.scope.project_ids
            else None,
            decision_unit_id=decision_unit_id,
            baseline_version_id=baseline.version_id,
            search_space_version_id=space.version_id,
            evaluation_space_version_id=evaluation_space_obj.version_id
            if evaluation_space_obj
            else None,
            members=members,
            stress_axes=stress_axes,
            search_space_state=space.state,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
            now=self.clock.now(),
        )
        self.repository.upsert_scenario_set(scenario_set)
        self.audit_writer.write(
            identity=identity,
            action="simulation.scenario_set.create",
            object_type="ScenarioSet",
            object_id=scenario_set.scenario_set_id,
            request_id=request_id,
            reason_code="SCENARIO_SET_DRAFT",
            outcome="ACCEPTED",
            object_version_id=scenario_set.version_id,
        )
        return scenario_set

    def freeze(
        self,
        *,
        identity: IdentityContext,
        scenario_set_id: UUID,
        request_id: str,
    ) -> ScenarioSet:
        require_audit(self.audit_writer)
        scenario_set = self.repository.get_scenario_set(
            scope=identity.scope, scenario_set_id=scenario_set_id
        )
        if scenario_set is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"场景集不存在 / Scenario set {scenario_set_id} not found in scope."),
            )
        validate_search_eval_independence(scenario_set)
        frozen = scenario_set.model_copy(
            update={
                "state": ScenarioSetState.FROZEN,
                "frozen_at": self.clock.now(),
                "frozen_by": identity.subject_id,
            }
        )
        self.repository.upsert_scenario_set(frozen)
        self.audit_writer.write(
            identity=identity,
            action="simulation.scenario_set.freeze",
            object_type="ScenarioSet",
            object_id=frozen.scenario_set_id,
            request_id=request_id,
            reason_code="SCENARIO_SET_FROZEN",
            outcome="ACCEPTED",
            object_version_id=frozen.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="simulation.scenario_sets_frozen.v1",
            aggregate_type="ScenarioSet",
            aggregate_id=frozen.scenario_set_id,
            payload={
                "scenario_set_id": str(frozen.scenario_set_id),
                "version_id": str(frozen.version_id),
                "decision_unit_id": str(frozen.decision_unit_id),
            },
            request_id=request_id,
        )
        return frozen

    def list(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[ScenarioSet, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        return self.repository.list_scenario_sets(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )

    def get(self, *, identity: IdentityContext, scenario_set_id: UUID) -> ScenarioSet:
        scenario_set = self.repository.get_scenario_set(
            scope=identity.scope, scenario_set_id=scenario_set_id
        )
        if scenario_set is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"场景集不存在 / Scenario set {scenario_set_id} not found in scope."),
            )
        return scenario_set


# ------------------------------------------------------------------ simulation batch
class SimulationBatchService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        baseline_id: UUID,
        scenario_set_id: UUID,
        award_mode: AwardMode,
        policy_threshold: str,
        request_id: str,
    ) -> SimulationBatch:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        baseline = self.repository.get_baseline(scope=identity.scope, baseline_id=baseline_id)
        if baseline is None or baseline.state != BaselineState.FROZEN:
            raise BiaiceError(
                "BASELINE_INCOMPLETE",
                detail=(
                    "决策基线必须处于 FROZEN 状态 / Decision baseline must be in FROZEN state."
                ),
            )
        scenario_set = self.repository.get_scenario_set(
            scope=identity.scope, scenario_set_id=scenario_set_id
        )
        if scenario_set is None or scenario_set.state != ScenarioSetState.FROZEN:
            raise BiaiceError(
                "SCENARIO_SET_INVALID",
                detail=(
                    "场景集必须先冻结 / Scenario set must be FROZEN before a simulation batch."
                ),
            )
        batch = SimulationBatch(
            batch_id=new_uuid(),
            version_id=new_uuid(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=identity.scope.project_ids.__iter__().__next__()
            if identity.scope.project_ids
            else None,
            decision_unit_id=decision_unit_id,
            baseline_version_id=baseline.version_id,
            scenario_set_version_id=scenario_set.version_id,
            award_mode=award_mode,
            state=BatchState.PENDING,
            policy_threshold=DecimalStr.coerce(policy_threshold),
            candidate_count=0,
            progress_percent=0,
            requested_by=identity.subject_id,
            created_at=self.clock.now(),
            last_updated_at=self.clock.now(),
        )
        self.repository.upsert_batch(batch)
        self.audit_writer.write(
            identity=identity,
            action="simulation.batch.create",
            object_type="SimulationBatch",
            object_id=batch.batch_id,
            request_id=request_id,
            reason_code="SIMULATION_BATCH_QUEUED",
            outcome="ACCEPTED",
            object_version_id=batch.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="simulation.simulation_started.v1",
            aggregate_type="SimulationBatch",
            aggregate_id=batch.batch_id,
            payload={
                "batch_id": str(batch.batch_id),
                "version_id": str(batch.version_id),
                "decision_unit_id": str(decision_unit_id),
                "scenario_set_version_id": str(scenario_set.version_id),
            },
            request_id=request_id,
        )
        return batch

    def cancel(
        self,
        *,
        identity: IdentityContext,
        batch_id: UUID,
        request_id: str,
    ) -> SimulationBatch:
        require_audit(self.audit_writer)
        batch = self.repository.get_batch(scope=identity.scope, batch_id=batch_id)
        if batch is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"仿真批次不存在 / Simulation batch {batch_id} not found in scope."),
            )
        if batch.state in {
            BatchState.SUCCEEDED,
            BatchState.INDETERMINATE,
            BatchState.FAILED_TERMINAL,
            BatchState.CANCELLED,
        }:
            raise BiaiceError(
                "JOB_NOT_CANCELLABLE",
                detail=(
                    f"仿真批次不可取消（state={batch.state}）/ Simulation batch cannot be cancelled."
                ),
            )
        cancelled = batch.model_copy(
            update={"state": BatchState.CANCELLED, "last_updated_at": self.clock.now()}
        )
        self.repository.upsert_batch(cancelled)
        self.audit_writer.write(
            identity=identity,
            action="simulation.batch.cancel",
            object_type="SimulationBatch",
            object_id=cancelled.batch_id,
            request_id=request_id,
            reason_code="USER_REQUEST",
            outcome="ACCEPTED",
            object_version_id=cancelled.version_id,
        )
        return cancelled

    def retry(
        self,
        *,
        identity: IdentityContext,
        batch_id: UUID,
        request_id: str,
    ) -> SimulationBatch:
        require_audit(self.audit_writer)
        batch = self.repository.get_batch(scope=identity.scope, batch_id=batch_id)
        if batch is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"仿真批次不存在 / Simulation batch {batch_id} not found in scope."),
            )
        if batch.state not in {BatchState.FAILED_RETRYABLE, BatchState.INDETERMINATE}:
            raise BiaiceError(
                "JOB_NOT_RETRYABLE",
                detail=(
                    f"仿真批次不可重试（state={batch.state}）/ Simulation batch cannot be retried."
                ),
            )
        retried = batch.model_copy(
            update={"state": BatchState.PENDING, "last_updated_at": self.clock.now()}
        )
        self.repository.upsert_batch(retried)
        self.audit_writer.write(
            identity=identity,
            action="simulation.batch.retry",
            object_type="SimulationBatch",
            object_id=retried.batch_id,
            request_id=request_id,
            reason_code="USER_REQUEST",
            outcome="ACCEPTED",
            object_version_id=retried.version_id,
        )
        return retried

    def list(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[SimulationBatch, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        return self.repository.list_batches(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get(self, *, identity: IdentityContext, batch_id: UUID) -> SimulationBatch:
        batch = self.repository.get_batch(scope=identity.scope, batch_id=batch_id)
        if batch is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"仿真批次不存在 / Simulation batch {batch_id} not found in scope."),
            )
        return batch

    # ----- internal helpers shared with workers and tests
    def run_static_validation(
        self,
        *,
        identity: IdentityContext,
        batch: SimulationBatch,
        candidates: Sequence[SimulationCandidate],
        context: StaticValidationContext,
        request_id: str,
    ) -> tuple[SimulationCandidate, tuple[StaticValidationResult, ...]]:
        results: list[StaticValidationResult] = []
        for candidate in candidates:
            result = validate_candidate(
                candidate=candidate,
                context=context,
                assessed_at=self.clock.now(),
            )
            self.repository.upsert_static_validation(result.validation)
            self.audit_writer.write(
                identity=identity,
                action="simulation.static_validation",
                object_type="StaticCandidateValidation",
                object_id=result.validation.validation_id,
                request_id=request_id,
                reason_code="STATIC_VALIDATION",
                outcome=result.validation.status.value,
            )
            results.append(result)
        assert_validation_passed(results)
        survivors = [
            candidate
            for candidate, result in zip(candidates, results)
            if result.validation.status == StaticValidationStatus.PASS
        ]
        updated_batch = batch.model_copy(
            update={
                "state": BatchState.RUNNING,
                "candidate_count": len(survivors),
                "last_updated_at": self.clock.now(),
                "progress_percent": 25,
            }
        )
        self.repository.upsert_batch(updated_batch)
        return tuple(survivors), tuple(results)

    def run_scenario_referees(
        self,
        *,
        identity: IdentityContext,
        batch: SimulationBatch,
        scenario_set: ScenarioSet,
        baseline_manifest_hash: str,
        candidates: Sequence[SimulationCandidate],
        seed: int,
    ) -> tuple[tuple[ScenarioOutcome, ...], tuple[ScenarioStrategyAssessment, ...]]:
        outcomes: list[ScenarioOutcome] = []
        assessments: list[ScenarioStrategyAssessment] = []
        for member in scenario_set.members:
            for candidate in candidates:
                if member.scenario_kind == ScenarioKind.STRESS:
                    continue
                referee = RefereeInput(
                    candidate_id=candidate.candidate_id,
                    scenario_id=member.scenario_id,
                    batch_id=batch.batch_id,
                    baseline_manifest_hash=baseline_manifest_hash,
                    scenario_kind=member.scenario_kind.value,
                    candidate_parameters=candidate.parameters,
                    scenario_parameters=member.params,
                    feasibility_threshold=Decimal("0"),
                    pay_off_lower=Decimal("0"),
                    pay_off_upper=Decimal("1"),
                    seed=seed,
                    review_validity=ReviewValidity.CURRENT,
                )
                output = evaluate_scenario(
                    referee,
                    assessed_at=self.clock.now(),
                    tenant_id=batch.tenant_id,
                    data_domain_id=batch.data_domain_id,
                    project_id=batch.project_id,
                    decision_unit_id=batch.decision_unit_id,
                )
                self.repository.upsert_scenario_outcome(output.outcome)
                self.repository.upsert_strategy_assessment(output.assessment)
                outcomes.append(output.outcome)
                assessments.append(output.assessment)
        return tuple(outcomes), tuple(assessments)


# ------------------------------------------------------------------ optimization
class OptimizationService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create_run(
        self,
        *,
        identity: IdentityContext,
        batch_id: UUID,
        objective_kind: ObjectiveKind,
        award_mode: AwardMode,
        policy_threshold: str,
        blueprints: Sequence[CandidateBlueprint],
        stress_axes: Sequence[StressAxis],
        stress_scenarios: Mapping[StressAxis, Sequence[StressScenario]],
        request_id: str,
    ) -> OptimizationRun:
        require_audit(self.audit_writer)
        batch = self.repository.get_batch(scope=identity.scope, batch_id=batch_id)
        if batch is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"仿真批次不存在 / Simulation batch {batch_id} not found in scope."),
            )
        candidates = generate_candidates(
            batch_id=batch.batch_id,
            version_id=new_uuid(),
            tenant_id=batch.tenant_id,
            data_domain_id=batch.data_domain_id,
            project_id=batch.project_id,
            decision_unit_id=batch.decision_unit_id,
            blueprints=blueprints,
            created_at=self.clock.now(),
        )
        for candidate in candidates:
            self.repository.upsert_candidate(candidate)
        run = OptimizationRun(
            run_id=new_uuid(),
            batch_id=batch.batch_id,
            version_id=new_uuid(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=identity.scope.project_ids.__iter__().__next__()
            if identity.scope.project_ids
            else None,
            decision_unit_id=batch.decision_unit_id,
            state=OptimizationState.RUNNING,
            award_mode=award_mode,
            objective_kind=objective_kind,
            policy_threshold=DecimalStr.coerce(policy_threshold),
            requested_by=identity.subject_id,
            created_at=self.clock.now(),
        )
        self.repository.upsert_optimization_run(run)
        self.audit_writer.write(
            identity=identity,
            action="simulation.optimization.run.create",
            object_type="OptimizationRun",
            object_id=run.run_id,
            request_id=request_id,
            reason_code="OPTIMIZATION_QUEUED",
            outcome="ACCEPTED",
            object_version_id=run.version_id,
        )
        # Stress axes run synchronously: hard-axis violation aborts the run.
        stress_report = run_stress_tests(
            run_id=run.run_id,
            candidates=candidates,
            scenarios=stress_scenarios,
            assessed_at=self.clock.now(),
            tenant_id=run.tenant_id,
            data_domain_id=run.data_domain_id,
            project_id=run.project_id,
            decision_unit_id=run.decision_unit_id,
        )
        for assessment in stress_report.assessments:
            self.repository.upsert_stress_assessment(assessment)
        if not stress_report.passed:
            failed_run = run.model_copy(
                update={
                    "state": OptimizationState.FAILED,
                    "invalidated_at": self.clock.now(),
                    "invalidated_by": identity.subject_id,
                }
            )
            self.repository.upsert_optimization_run(failed_run)
            self.audit_writer.write(
                identity=identity,
                action="simulation.optimization.run.stress_failed",
                object_type="OptimizationRun",
                object_id=failed_run.run_id,
                request_id=request_id,
                reason_code="STRESS_AXIS_VIOLATED",
                outcome="FAILED",
                object_version_id=failed_run.version_id,
            )
            return failed_run
        assert_no_stress_axis_in_probability({axis: Decimal("0") for axis in stress_axes})
        return run

    def finalize(
        self,
        *,
        identity: IdentityContext,
        run_id: UUID,
        request_id: str,
    ) -> OptimizationRun:
        require_audit(self.audit_writer)
        run = self.repository.get_optimization_run(scope=identity.scope, run_id=run_id)
        if run is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"优化运行不存在 / Optimization run {run_id} not found in scope."),
            )
        if run.state not in {OptimizationState.SUCCEEDED, OptimizationState.RUNNING}:
            raise BiaiceError(
                "INVALID_IDEMPOTENCY_KEY",
                detail=(
                    f"优化运行不可 finalize（state={run.state}）/ Optimization run is not "
                    "ready to be finalized."
                ),
            )
        finalized = run.model_copy(
            update={"state": OptimizationState.FINALIZED, "finalized_at": self.clock.now()}
        )
        self.repository.upsert_optimization_run(finalized)
        self.audit_writer.write(
            identity=identity,
            action="simulation.optimization.run.finalize",
            object_type="OptimizationRun",
            object_id=finalized.run_id,
            request_id=request_id,
            reason_code="OPTIMIZATION_FINALIZED",
            outcome="ACCEPTED",
            object_version_id=finalized.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="simulation.strategy_plans_finalized.v1",
            aggregate_type="OptimizationRun",
            aggregate_id=finalized.run_id,
            payload={"run_id": str(finalized.run_id)},
            request_id=request_id,
        )
        return finalized

    def invalidate(
        self,
        *,
        identity: IdentityContext,
        run_id: UUID,
        request_id: str,
    ) -> OptimizationRun:
        require_audit(self.audit_writer)
        run = self.repository.get_optimization_run(scope=identity.scope, run_id=run_id)
        if run is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"优化运行不存在 / Optimization run {run_id} not found in scope."),
            )
        invalidated = run.model_copy(
            update={
                "state": OptimizationState.INVALIDATED,
                "invalidated_at": self.clock.now(),
                "invalidated_by": identity.subject_id,
            }
        )
        self.repository.upsert_optimization_run(invalidated)
        self.audit_writer.write(
            identity=identity,
            action="simulation.optimization.run.invalidate",
            object_type="OptimizationRun",
            object_id=invalidated.run_id,
            request_id=request_id,
            reason_code="USER_REQUEST",
            outcome="ACCEPTED",
            object_version_id=invalidated.version_id,
        )
        return invalidated

    def merge_plans(
        self,
        *,
        identity: IdentityContext,
        run_id: UUID,
        plan_id: UUID,
        candidate_ids: Sequence[UUID],
        linkage: str,
        tau_b: str,
        tau_m: str,
        request_id: str,
    ) -> MergeAssessment:
        require_audit(self.audit_writer)
        run = self.repository.get_optimization_run(scope=identity.scope, run_id=run_id)
        if run is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"优化运行不存在 / Optimization run {run_id} not found in scope."),
            )
        assessment = merge_assessments(
            MergeRequest(
                plan_id=plan_id,
                run_id=run_id,
                baseline_version_id=run.linked_run_version_id()
                if hasattr(run, "linked_run_version_id")
                else run.version_id,
                candidate_ids=tuple(candidate_ids),
                linkage=linkage,
                tau_b=DecimalStr.coerce(tau_b),
                tau_m=DecimalStr.coerce(tau_m),
            ),
            assessed_at=self.clock.now(),
            tenant_id=run.tenant_id,
            data_domain_id=run.data_domain_id,
            project_id=run.project_id,
            decision_unit_id=run.decision_unit_id,
        )
        self.repository.upsert_merge_assessment(assessment)
        self.audit_writer.write(
            identity=identity,
            action="simulation.optimization.merge",
            object_type="MergeAssessment",
            object_id=assessment.merge_id,
            request_id=request_id,
            reason_code="PLAN_MERGE",
            outcome="ACCEPTED" if assessment.accepted else "BLOCKED",
        )
        assert_merge_accepted(assessment)
        return assessment

    def list(self, *, identity: IdentityContext, batch_id: UUID) -> tuple[OptimizationRun, ...]:
        return self.repository.list_optimization_runs(scope=identity.scope, batch_id=batch_id)

    def get(self, *, identity: IdentityContext, run_id: UUID) -> OptimizationRun:
        run = self.repository.get_optimization_run(scope=identity.scope, run_id=run_id)
        if run is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"优化运行不存在 / Optimization run {run_id} not found in scope."),
            )
        return run

    def list_stress(
        self, *, identity: IdentityContext, run_id: UUID
    ) -> tuple[StressTestAssessment, ...]:
        return self.repository.list_stress_assessments(scope=identity.scope, run_id=run_id)

    def list_plans(self, *, identity: IdentityContext, run_id: UUID) -> tuple[StrategyPlan, ...]:
        return self.repository.list_strategy_plans(scope=identity.scope, run_id=run_id)

    def list_merge_assessments(
        self, *, identity: IdentityContext, run_id: UUID
    ) -> tuple[MergeAssessment, ...]:
        return self.repository.list_merge_assessments(scope=identity.scope, run_id=run_id)

    def publish_plan(
        self,
        *,
        identity: IdentityContext,
        plan_id: UUID,
        request_id: str,
    ) -> StrategyPlan:
        require_audit(self.audit_writer)
        plan = self.repository.get_strategy_plan(scope=identity.scope, plan_id=plan_id)
        if plan is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"方案不存在 / Strategy plan {plan_id} not found in scope."),
            )
        if plan.state not in {PlanState.DRAFT}:
            raise BiaiceError(
                "JOB_NOT_CANCELLABLE",
                detail=(f"方案不可发布（state={plan.state}）/ Strategy plan cannot be published."),
            )
        published = plan.model_copy(
            update={
                "state": PlanState.PUBLISHED,
                "published_at": self.clock.now(),
                "published_by": identity.subject_id,
            }
        )
        self.repository.upsert_strategy_plan(published)
        self.audit_writer.write(
            identity=identity,
            action="simulation.plan.publish",
            object_type="StrategyPlan",
            object_id=published.plan_id,
            request_id=request_id,
            reason_code="PLAN_PUBLISH",
            outcome="ACCEPTED",
            object_version_id=published.version_id,
        )
        return published

    def invalidate_plan(
        self,
        *,
        identity: IdentityContext,
        plan_id: UUID,
        request_id: str,
    ) -> StrategyPlan:
        require_audit(self.audit_writer)
        plan = self.repository.get_strategy_plan(scope=identity.scope, plan_id=plan_id)
        if plan is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"方案不存在 / Strategy plan {plan_id} not found in scope."),
            )
        invalidated = plan.model_copy(
            update={
                "state": PlanState.INVALIDATED,
                "invalidated_at": self.clock.now(),
                "invalidated_by": identity.subject_id,
            }
        )
        self.repository.upsert_strategy_plan(invalidated)
        self.audit_writer.write(
            identity=identity,
            action="simulation.plan.invalidate",
            object_type="StrategyPlan",
            object_id=invalidated.plan_id,
            request_id=request_id,
            reason_code="USER_REQUEST",
            outcome="ACCEPTED",
            object_version_id=invalidated.version_id,
        )
        return invalidated


# ------------------------------------------------------------------ eligibility
class EligibilityService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def assess(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        baseline_id: UUID,
        snapshot_id: UUID | None,
        inputs: GateInputs,
        request_id: str,
    ) -> RecommendationEligibility:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        baseline = self.repository.get_baseline(scope=identity.scope, baseline_id=baseline_id)
        if baseline is None or baseline.state not in {
            BaselineState.FROZEN,
            BaselineState.SUPERSEDED,
        }:
            raise BiaiceError(
                "ELIGIBILITY_INPUT_UNKNOWN",
                detail=(
                    "决策基线未处于 FROZEN 或 SUPERSEDED 状态 / Decision baseline is not "
                    "FROZEN or SUPERSEDED; eligibility cannot be assessed."
                ),
            )
        if snapshot_id is not None:
            snapshot = self.repository.get_snapshot(scope=identity.scope, snapshot_id=snapshot_id)
            if snapshot is None or snapshot.state != SnapshotState.LOCKED:
                raise BiaiceError(
                    "ELIGIBILITY_INPUT_UNKNOWN",
                    detail=(
                        "评估快照必须处于 LOCKED 状态 / Simulation assessment snapshot must "
                        "be LOCKED before eligibility can be assessed."
                    ),
                )
        result = assess_eligibility(inputs)
        eligibility = RecommendationEligibility(
            eligibility_id=new_uuid(),
            version_id=new_uuid(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=identity.scope.project_ids.__iter__().__next__()
            if identity.scope.project_ids
            else None,
            decision_unit_id=decision_unit_id,
            state=result.state,
            blocked_reason_codes=result.blocked_reason_codes,
            upstream_validity=dict(result.upstream_validity),
            baseline_version_id=baseline.version_id,
            snapshot_version_id=(
                self.repository.get_snapshot(
                    scope=identity.scope, snapshot_id=snapshot_id
                ).version_id
                if snapshot_id is not None
                else None
            ),
            assessed_at=self.clock.now(),
            assessed_by=identity.subject_id,
        )
        self.repository.upsert_recommendation_eligibility(eligibility)
        self.audit_writer.write(
            identity=identity,
            action="simulation.eligibility.assess",
            object_type="RecommendationEligibility",
            object_id=eligibility.eligibility_id,
            request_id=request_id,
            reason_code="ELIGIBILITY_ASSESSED",
            outcome=eligibility.state.value,
            object_version_id=eligibility.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="simulation.eligibility_assessed.v1",
            aggregate_type="RecommendationEligibility",
            aggregate_id=eligibility.eligibility_id,
            payload={
                "eligibility_id": str(eligibility.eligibility_id),
                "decision_unit_id": str(decision_unit_id),
                "state": eligibility.state.value,
            },
            request_id=request_id,
        )
        assert_eligibility_for_recommendation(result)
        return eligibility

    def list(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[RecommendationEligibility, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        return self.repository.list_recommendation_eligibilities(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )

    def get(self, *, identity: IdentityContext, eligibility_id: UUID) -> RecommendationEligibility:
        eligibility = self.repository.get_recommendation_eligibility(
            scope=identity.scope, eligibility_id=eligibility_id
        )
        if eligibility is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(
                    f"推荐资格不存在 / Recommendation eligibility {eligibility_id} not found in scope."
                ),
            )
        return eligibility


# ------------------------------------------------------------------ snapshot
class SnapshotService:
    def __init__(
        self,
        *,
        repository: InMemorySimulationRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        payload: Mapping[str, Any],
        request_id: str,
    ) -> SimulationAssessmentSnapshot:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        snapshot = create_snapshot(
            SnapshotRequest(
                snapshot_id=new_uuid(),
                version_id=new_uuid(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                project_id=identity.scope.project_ids.__iter__().__next__()
                if identity.scope.project_ids
                else None,
                decision_unit_id=decision_unit_id,
                payload=payload,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                lock=True,
            )
        )
        assert_shadow_watermark(snapshot)
        self.repository.upsert_snapshot(snapshot)
        self.audit_writer.write(
            identity=identity,
            action="simulation.snapshot.create",
            object_type="SimulationAssessmentSnapshot",
            object_id=snapshot.snapshot_id,
            request_id=request_id,
            reason_code="SNAPSHOT_LOCKED",
            outcome="ACCEPTED",
            object_version_id=snapshot.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="simulation.simulation_snapshot_created.v1",
            aggregate_type="SimulationAssessmentSnapshot",
            aggregate_id=snapshot.snapshot_id,
            payload={
                "snapshot_id": str(snapshot.snapshot_id),
                "watermark": snapshot.watermark,
                "payload_hash": snapshot.payload_hash,
            },
            request_id=request_id,
        )
        return snapshot

    def list(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[SimulationAssessmentSnapshot, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        return self.repository.list_snapshots(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )

    def get(self, *, identity: IdentityContext, snapshot_id: UUID) -> SimulationAssessmentSnapshot:
        snapshot = self.repository.get_snapshot(scope=identity.scope, snapshot_id=snapshot_id)
        if snapshot is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"快照不存在 / Snapshot {snapshot_id} not found in scope."),
            )
        return snapshot

    def download(
        self, *, identity: IdentityContext, snapshot_id: UUID
    ) -> SimulationAssessmentSnapshot:
        snapshot = self.get(identity=identity, snapshot_id=snapshot_id)
        assert_shadow_watermark(snapshot)
        return snapshot
