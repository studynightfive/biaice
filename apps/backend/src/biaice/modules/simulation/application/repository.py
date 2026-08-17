"""In-memory simulation repository — single-process truth for M0.

The repository owns the canonical aggregates and is the only writer for
frozen Pydantic models. It exposes typed query helpers (filtered by scope,
sorted deterministically) and a private `upsert` used by the application
services. Production deployment will swap this for a SQLAlchemy adapter that
implements the same Protocol; that PR is explicitly out of scope here.

Thread-safety: the in-memory store uses a single `threading.Lock` because
the simulation services are also exercised from FastAPI's threaded executor.
Tests that mount multiple `InMemorySimulationRepository` instances obtain
independent snapshots and therefore deterministic behaviour.
"""
from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.simulation.domain.models import (
    CandidateSearchSpace,
    DecisionBaseline,
    MergeAssessment,
    OptimizationRun,
    RecommendationEligibility,
    ScenarioOutcome,
    ScenarioSet,
    ScenarioStrategyAssessment,
    SimulationAssessmentSnapshot,
    SimulationBatch,
    SimulationCandidate,
    StaticCandidateValidation,
    StrategyPlan,
    StressTestAssessment,
)


class SimulationRepository(Protocol):
    def upsert_baseline(self, baseline: DecisionBaseline) -> None: ...
    def upsert_search_space(self, space: CandidateSearchSpace) -> None: ...
    def upsert_scenario_set(self, scenario_set: ScenarioSet) -> None: ...
    def upsert_batch(self, batch: SimulationBatch) -> None: ...
    def upsert_candidate(self, candidate: SimulationCandidate) -> None: ...
    def upsert_static_validation(self, validation: StaticCandidateValidation) -> None: ...
    def upsert_scenario_outcome(self, outcome: ScenarioOutcome) -> None: ...
    def upsert_strategy_assessment(self, assessment: ScenarioStrategyAssessment) -> None: ...
    def upsert_optimization_run(self, run: OptimizationRun) -> None: ...
    def upsert_stress_assessment(self, assessment: StressTestAssessment) -> None: ...
    def upsert_strategy_plan(self, plan: StrategyPlan) -> None: ...
    def upsert_merge_assessment(self, assessment: MergeAssessment) -> None: ...
    def upsert_recommendation_eligibility(self, eligibility: RecommendationEligibility) -> None: ...
    def upsert_snapshot(self, snapshot: SimulationAssessmentSnapshot) -> None: ...
    def get_baseline(self, scope: TenantScope, baseline_id: UUID) -> DecisionBaseline | None: ...
    def get_search_space(self, scope: TenantScope, search_space_id: UUID) -> CandidateSearchSpace | None: ...
    def get_scenario_set(self, scope: TenantScope, scenario_set_id: UUID) -> ScenarioSet | None: ...
    def get_batch(self, scope: TenantScope, batch_id: UUID) -> SimulationBatch | None: ...
    def get_optimization_run(self, scope: TenantScope, run_id: UUID) -> OptimizationRun | None: ...
    def get_strategy_plan(self, scope: TenantScope, plan_id: UUID) -> StrategyPlan | None: ...
    def get_recommendation_eligibility(self, scope: TenantScope, eligibility_id: UUID) -> RecommendationEligibility | None: ...
    def get_snapshot(self, scope: TenantScope, snapshot_id: UUID) -> SimulationAssessmentSnapshot | None: ...
    def list_baselines(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[DecisionBaseline, ...]: ...
    def list_search_spaces(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[CandidateSearchSpace, ...]: ...
    def list_scenario_sets(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[ScenarioSet, ...]: ...
    def list_batches(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[SimulationBatch, ...]: ...
    def list_candidates(self, scope: TenantScope, batch_id: UUID) -> tuple[SimulationCandidate, ...]: ...
    def list_static_validations(self, scope: TenantScope, batch_id: UUID) -> tuple[StaticCandidateValidation, ...]: ...
    def list_scenario_outcomes(self, scope: TenantScope, batch_id: UUID) -> tuple[ScenarioOutcome, ...]: ...
    def list_strategy_assessments(self, scope: TenantScope, batch_id: UUID) -> tuple[ScenarioStrategyAssessment, ...]: ...
    def list_optimization_runs(self, scope: TenantScope, batch_id: UUID) -> tuple[OptimizationRun, ...]: ...
    def list_stress_assessments(self, scope: TenantScope, run_id: UUID) -> tuple[StressTestAssessment, ...]: ...
    def list_strategy_plans(self, scope: TenantScope, run_id: UUID) -> tuple[StrategyPlan, ...]: ...
    def list_merge_assessments(self, scope: TenantScope, run_id: UUID) -> tuple[MergeAssessment, ...]: ...
    def list_recommendation_eligibilities(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[RecommendationEligibility, ...]: ...
    def list_snapshots(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[SimulationAssessmentSnapshot, ...]: ...


def _scope_matches(item, scope: TenantScope) -> bool:
    if item.tenant_id != scope.tenant_id or item.data_domain_id != scope.data_domain_id:
        return False
    if item.project_id is not None and not scope.all_projects and item.project_id not in scope.project_ids:
        return False
    if (
        getattr(item, "decision_unit_id", None) is not None
        and not scope.all_decision_units
        and getattr(item, "decision_unit_id", None) not in scope.decision_unit_ids
    ):
        return False
    return True


class InMemorySimulationRepository:
    """Thread-safe in-memory simulation repository."""

    def __init__(self) -> None:
        self._baselines: dict[UUID, DecisionBaseline] = {}
        self._search_spaces: dict[UUID, CandidateSearchSpace] = {}
        self._scenario_sets: dict[UUID, ScenarioSet] = {}
        self._batches: dict[UUID, SimulationBatch] = {}
        self._candidates: dict[UUID, SimulationCandidate] = {}
        self._static_validations: dict[UUID, StaticCandidateValidation] = {}
        self._scenario_outcomes: dict[UUID, ScenarioOutcome] = {}
        self._strategy_assessments: dict[UUID, ScenarioStrategyAssessment] = {}
        self._optimization_runs: dict[UUID, OptimizationRun] = {}
        self._stress_assessments: dict[UUID, StressTestAssessment] = {}
        self._strategy_plans: dict[UUID, StrategyPlan] = {}
        self._merge_assessments: dict[UUID, MergeAssessment] = {}
        self._recommendation_eligibilities: dict[UUID, RecommendationEligibility] = {}
        self._snapshots: dict[UUID, SimulationAssessmentSnapshot] = {}
        self._lock = threading.Lock()

    def _all(self, store: dict, scope: TenantScope, *, decision_unit_id: UUID | None = None) -> tuple:
        with self._lock:
            results = [
                item
                for item in store.values()
                if _scope_matches(item, scope)
                and (decision_unit_id is None or getattr(item, "decision_unit_id", None) == decision_unit_id)
            ]
        results.sort(key=lambda item: (str(getattr(item, "decision_unit_id", "")), str(item.version_id), str(getattr(item, "created_at", ""))))
        return tuple(results)

    def upsert_baseline(self, baseline: DecisionBaseline) -> None:
        with self._lock:
            self._baselines[baseline.baseline_id] = baseline

    def upsert_search_space(self, space: CandidateSearchSpace) -> None:
        with self._lock:
            self._search_spaces[space.search_space_id] = space

    def upsert_scenario_set(self, scenario_set: ScenarioSet) -> None:
        with self._lock:
            self._scenario_sets[scenario_set.scenario_set_id] = scenario_set

    def upsert_batch(self, batch: SimulationBatch) -> None:
        with self._lock:
            self._batches[batch.batch_id] = batch

    def upsert_candidate(self, candidate: SimulationCandidate) -> None:
        with self._lock:
            self._candidates[candidate.candidate_id] = candidate

    def upsert_static_validation(self, validation: StaticCandidateValidation) -> None:
        with self._lock:
            self._static_validations[validation.validation_id] = validation

    def upsert_scenario_outcome(self, outcome: ScenarioOutcome) -> None:
        with self._lock:
            self._scenario_outcomes[outcome.outcome_id] = outcome

    def upsert_strategy_assessment(self, assessment: ScenarioStrategyAssessment) -> None:
        with self._lock:
            self._strategy_assessments[assessment.assessment_id] = assessment

    def upsert_optimization_run(self, run: OptimizationRun) -> None:
        with self._lock:
            self._optimization_runs[run.run_id] = run

    def upsert_stress_assessment(self, assessment: StressTestAssessment) -> None:
        with self._lock:
            self._stress_assessments[assessment.assessment_id] = assessment

    def upsert_strategy_plan(self, plan: StrategyPlan) -> None:
        with self._lock:
            self._strategy_plans[plan.plan_id] = plan

    def upsert_merge_assessment(self, assessment: MergeAssessment) -> None:
        with self._lock:
            self._merge_assessments[assessment.merge_id] = assessment

    def upsert_recommendation_eligibility(self, eligibility: RecommendationEligibility) -> None:
        with self._lock:
            self._recommendation_eligibilities[eligibility.eligibility_id] = eligibility

    def upsert_snapshot(self, snapshot: SimulationAssessmentSnapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot

    def get_baseline(self, scope: TenantScope, baseline_id: UUID) -> DecisionBaseline | None:
        with self._lock:
            item = self._baselines.get(baseline_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_search_space(self, scope: TenantScope, search_space_id: UUID) -> CandidateSearchSpace | None:
        with self._lock:
            item = self._search_spaces.get(search_space_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_scenario_set(self, scope: TenantScope, scenario_set_id: UUID) -> ScenarioSet | None:
        with self._lock:
            item = self._scenario_sets.get(scenario_set_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_batch(self, scope: TenantScope, batch_id: UUID) -> SimulationBatch | None:
        with self._lock:
            item = self._batches.get(batch_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_optimization_run(self, scope: TenantScope, run_id: UUID) -> OptimizationRun | None:
        with self._lock:
            item = self._optimization_runs.get(run_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_strategy_plan(self, scope: TenantScope, plan_id: UUID) -> StrategyPlan | None:
        with self._lock:
            item = self._strategy_plans.get(plan_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_recommendation_eligibility(self, scope: TenantScope, eligibility_id: UUID) -> RecommendationEligibility | None:
        with self._lock:
            item = self._recommendation_eligibilities.get(eligibility_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def get_snapshot(self, scope: TenantScope, snapshot_id: UUID) -> SimulationAssessmentSnapshot | None:
        with self._lock:
            item = self._snapshots.get(snapshot_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def list_baselines(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[DecisionBaseline, ...]:
        return self._all(self._baselines, scope, decision_unit_id=decision_unit_id)

    def list_search_spaces(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[CandidateSearchSpace, ...]:
        return self._all(self._search_spaces, scope, decision_unit_id=decision_unit_id)

    def list_scenario_sets(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[ScenarioSet, ...]:
        return self._all(self._scenario_sets, scope, decision_unit_id=decision_unit_id)

    def list_batches(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[SimulationBatch, ...]:
        return self._all(self._batches, scope, decision_unit_id=decision_unit_id)

    def list_candidates(self, scope: TenantScope, batch_id: UUID) -> tuple[SimulationCandidate, ...]:
        with self._lock:
            results = [
                item
                for item in self._candidates.values()
                if _scope_matches(item, scope) and item.batch_id == batch_id
            ]
        results.sort(key=lambda item: (str(item.candidate_id),))
        return tuple(results)

    def list_static_validations(self, scope: TenantScope, batch_id: UUID) -> tuple[StaticCandidateValidation, ...]:
        with self._lock:
            results = [
                item
                for item in self._static_validations.values()
                if _scope_matches(item, scope) and item.batch_id == batch_id
            ]
        results.sort(key=lambda item: str(item.validation_id))
        return tuple(results)

    def list_scenario_outcomes(self, scope: TenantScope, batch_id: UUID) -> tuple[ScenarioOutcome, ...]:
        with self._lock:
            results = [
                item
                for item in self._scenario_outcomes.values()
                if _scope_matches(item, scope) and item.batch_id == batch_id
            ]
        results.sort(key=lambda item: (str(item.scenario_id), str(item.candidate_id)))
        return tuple(results)

    def list_strategy_assessments(self, scope: TenantScope, batch_id: UUID) -> tuple[ScenarioStrategyAssessment, ...]:
        with self._lock:
            results = [
                item
                for item in self._strategy_assessments.values()
                if _scope_matches(item, scope) and item.batch_id == batch_id
            ]
        results.sort(key=lambda item: (str(item.scenario_id), str(item.candidate_id)))
        return tuple(results)

    def list_optimization_runs(self, scope: TenantScope, batch_id: UUID) -> tuple[OptimizationRun, ...]:
        with self._lock:
            results = [
                item
                for item in self._optimization_runs.values()
                if _scope_matches(item, scope) and item.batch_id == batch_id
            ]
        results.sort(key=lambda item: (item.created_at, str(item.run_id)))
        return tuple(results)

    def list_stress_assessments(self, scope: TenantScope, run_id: UUID) -> tuple[StressTestAssessment, ...]:
        with self._lock:
            results = [
                item
                for item in self._stress_assessments.values()
                if _scope_matches(item, scope) and item.run_id == run_id
            ]
        results.sort(key=lambda item: (str(item.axis), str(item.assessment_id)))
        return tuple(results)

    def list_strategy_plans(self, scope: TenantScope, run_id: UUID) -> tuple[StrategyPlan, ...]:
        with self._lock:
            results = [
                item
                for item in self._strategy_plans.values()
                if _scope_matches(item, scope) and item.run_id == run_id
            ]
        results.sort(key=lambda item: (item.created_at, str(item.plan_id)))
        return tuple(results)

    def list_merge_assessments(self, scope: TenantScope, run_id: UUID) -> tuple[MergeAssessment, ...]:
        with self._lock:
            results = [
                item
                for item in self._merge_assessments.values()
                if _scope_matches(item, scope) and item.run_id == run_id
            ]
        results.sort(key=lambda item: (item.assessed_at, str(item.merge_id)))
        return tuple(results)

    def list_recommendation_eligibilities(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[RecommendationEligibility, ...]:
        return self._all(self._recommendation_eligibilities, scope, decision_unit_id=decision_unit_id)

    def list_snapshots(self, scope: TenantScope, decision_unit_id: UUID) -> tuple[SimulationAssessmentSnapshot, ...]:
        return self._all(self._snapshots, scope, decision_unit_id=decision_unit_id)
