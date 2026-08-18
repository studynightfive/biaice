"""Optimization candidate generation, ranking and selection.

Candidate generation samples deterministic positions from the frozen candidate
search space; ranking orders them by the chosen objective kind; selection picks
0–4 candidates that satisfy the policy threshold.

The selection function never invents feasible plans: when no candidate clears
the threshold the function returns an empty plan and the service layer marks
the run INDETERMINATE. Stress axes are completely absent here; they live in
`stress.run_stress_tests`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, Sequence
from uuid import UUID, uuid4

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    AwardMode,
    DecimalStr,
    ObjectiveKind,
    SimulationCandidate,
)


@dataclass(frozen=True, slots=True)
class CandidateBlueprint:
    """Materialised search-space position produced by the optimization generator."""

    label: str
    parameters: dict[str, Any]
    expected_cost: Decimal
    expected_margin: Decimal


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    candidate: SimulationCandidate
    score: Decimal


@dataclass(frozen=True, slots=True)
class SelectionPlan:
    award_mode: AwardMode
    objective_kind: ObjectiveKind
    selected: tuple[SimulationCandidate, ...]
    total_expected_cost: DecimalStr
    total_expected_margin: DecimalStr


def _hash_to_decimal(*parts: Any) -> Decimal:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).digest()
    raw = int.from_bytes(digest[:8], "big")
    return Decimal(raw % 10_000_000) / Decimal(10_000_000)


def generate_candidates(
    *,
    batch_id: UUID,
    version_id: UUID,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID,
    blueprints: Sequence[CandidateBlueprint],
    created_at,
) -> tuple[SimulationCandidate, ...]:
    """Materialise candidate blueprints into immutable SimulationCandidate rows."""
    if not blueprints:
        return ()
    candidates: list[SimulationCandidate] = []
    for index, blueprint in enumerate(blueprints):
        candidates.append(
            SimulationCandidate(
                candidate_id=uuid4(),
                batch_id=batch_id,
                version_id=version_id,
                tenant_id=tenant_id,
                data_domain_id=data_domain_id,
                project_id=project_id,
                decision_unit_id=decision_unit_id,
                label=f"{blueprint.label}#{index + 1}",
                parameters=dict(blueprint.parameters),
                expected_cost=DecimalStr.from_decimal(blueprint.expected_cost),
                expected_margin=DecimalStr.from_decimal(blueprint.expected_margin),
                created_at=created_at,
            )
        )
    return tuple(candidates)


def rank_candidates(
    candidates: Iterable[SimulationCandidate],
    *,
    objective_kind: ObjectiveKind,
) -> tuple[RankedCandidate, ...]:
    """Order candidates by the objective; ties broken by deterministic UUID."""
    pairs: list[tuple[Decimal, SimulationCandidate]] = []
    for candidate in candidates:
        cost = Decimal(candidate.expected_cost.value)
        margin = Decimal(candidate.expected_margin.value)
        if objective_kind == ObjectiveKind.COST_MIN:
            score = -cost
        elif objective_kind == ObjectiveKind.MARGIN_MAX:
            score = margin
        elif objective_kind == ObjectiveKind.COVERAGE_MAX:
            score = margin - Decimal("0.25") * cost
        elif objective_kind == ObjectiveKind.RISK_MIN:
            score = -cost * Decimal("0.5") + margin
        else:
            raise BiaiceError(
                "INVALID_IDEMPOTENCY_KEY",
                detail=(f"未知的优化目标 / Unknown optimization objective: {objective_kind}."),
            )
        pairs.append((score, candidate))
    pairs.sort(key=lambda item: (-item[0], str(item[1].candidate_id)))
    return tuple(RankedCandidate(candidate=item[1], score=item[0]) for item in pairs)


def select_objective_candidates(
    *,
    ranked: Sequence[RankedCandidate],
    policy_threshold: DecimalStr,
    award_mode: AwardMode,
    objective_kind: ObjectiveKind,
) -> SelectionPlan:
    """Return the chosen candidates; empty tuple when none clear the threshold."""
    threshold = Decimal(policy_threshold.value)
    selected: list[SimulationCandidate] = []
    total_cost = Decimal("0")
    total_margin = Decimal("0")
    for ranked_item in ranked:
        margin = Decimal(ranked_item.candidate.expected_margin.value)
        if margin < threshold:
            continue
        selected.append(ranked_item.candidate)
        total_cost += Decimal(ranked_item.candidate.expected_cost.value)
        total_margin += margin
        if award_mode == AwardMode.SINGLE:
            break
        if award_mode == AwardMode.MULTI and len(selected) >= 4:
            break
    if not selected:
        return SelectionPlan(
            award_mode=award_mode,
            objective_kind=objective_kind,
            selected=(),
            total_expected_cost=DecimalStr.from_decimal(Decimal("0")),
            total_expected_margin=DecimalStr.from_decimal(Decimal("0")),
        )
    return SelectionPlan(
        award_mode=award_mode,
        objective_kind=objective_kind,
        selected=tuple(selected),
        total_expected_cost=DecimalStr.from_decimal(total_cost),
        total_expected_margin=DecimalStr.from_decimal(total_margin),
    )


def _coerce_score(value: Decimal) -> Decimal:
    return value
