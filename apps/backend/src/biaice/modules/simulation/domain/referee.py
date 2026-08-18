"""Deterministic scenario referee.

The referee is pure: given (candidate, scenario, baseline_manifest_hash, seed)
it returns a ScenarioOutcome. It never reads live upstream state; the manifest
hash is part of the deterministic input so a frozen baseline can never be
silently bypassed. `reviewed_pending` scenarios never enter the probability
denominator; the service layer keeps them in a separate tuple on the batch.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID

from biaice.modules.simulation.domain.models import (
    DecimalStr,
    ReviewValidity,
    ScenarioOutcome,
    ScenarioStrategyAssessment,
    new_uuid,
)


@dataclass(frozen=True, slots=True)
class RefereeInput:
    candidate_id: UUID
    scenario_id: UUID
    batch_id: UUID
    baseline_manifest_hash: str
    scenario_kind: str
    candidate_parameters: Mapping[str, Any]
    scenario_parameters: Mapping[str, Any]
    feasibility_threshold: Decimal
    pay_off_lower: Decimal
    pay_off_upper: Decimal
    seed: int
    review_validity: ReviewValidity


@dataclass(frozen=True, slots=True)
class RefereeOutput:
    outcome: ScenarioOutcome
    assessment: ScenarioStrategyAssessment
    reviewed_pending: bool


def evaluate_scenario(input: RefereeInput, *, assessed_at, tenant_id, data_domain_id,
                       project_id, decision_unit_id) -> RefereeOutput:
    """Deterministically map (candidate, scenario) → (outcome, assessment)."""
    if input.review_validity != ReviewValidity.CURRENT:
        return RefereeOutput(
            outcome=ScenarioOutcome(
                outcome_id=new_uuid(),
                candidate_id=input.candidate_id,
                scenario_id=input.scenario_id,
                batch_id=input.batch_id,
                tenant_id=tenant_id,
                data_domain_id=data_domain_id,
                project_id=project_id,
                decision_unit_id=decision_unit_id,
                feasible=False,
                expected_payoff=DecimalStr.from_decimal(Decimal("0")),
                p_win=DecimalStr.from_decimal(Decimal("0")),
                evaluated_at=assessed_at,
                review_validity=input.review_validity,
                detail=(
                    "上游评审尚未 CURRENT / Upstream review is not CURRENT; "
                    "scenario outcome stays UNDEFINED for the probability denominator."
                ),
            ),
            assessment=ScenarioStrategyAssessment(
                assessment_id=new_uuid(),
                candidate_id=input.candidate_id,
                scenario_id=input.scenario_id,
                batch_id=input.batch_id,
                tenant_id=tenant_id,
                data_domain_id=data_domain_id,
                project_id=project_id,
                decision_unit_id=decision_unit_id,
                review_validity=input.review_validity,
                summary=(
                    "Scenario excluded from probability because upstream review is "
                    f"{input.review_validity.value}."
                ),
                recommended=False,
                assessed_at=assessed_at,
                reason_code="REVIEW_NOT_CURRENT",
            ),
            reviewed_pending=True,
        )

    digest = hashlib.sha256(
        f"{input.candidate_id}|{input.scenario_id}|{input.baseline_manifest_hash}|"
        f"{input.seed}|{input.scenario_kind}".encode("utf-8")
    ).digest()
    raw = int.from_bytes(digest[:8], "big")
    fraction = (raw % 10_000) / 10_000  # uniform on [0, 1)
    score = input.pay_off_lower + (input.pay_off_upper - input.pay_off_lower) * Decimal(fraction)
    feasible = score >= input.feasibility_threshold
    p_win = Decimal(fraction)
    outcome = ScenarioOutcome(
        outcome_id=new_uuid(),
        candidate_id=input.candidate_id,
        scenario_id=input.scenario_id,
        batch_id=input.batch_id,
        tenant_id=tenant_id,
        data_domain_id=data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        feasible=feasible,
        expected_payoff=DecimalStr.from_decimal(score.quantize(Decimal("0.0001"))),
        p_win=DecimalStr.from_decimal(p_win.quantize(Decimal("0.0001"))),
        evaluated_at=assessed_at,
        review_validity=input.review_validity,
        detail=None,
    )
    summary = (
        f"feasible={feasible}; expected_payoff={outcome.expected_payoff.value}; "
        f"p_win={outcome.p_win.value}"
    )
    assessment = ScenarioStrategyAssessment(
        assessment_id=new_uuid(),
        candidate_id=input.candidate_id,
        scenario_id=input.scenario_id,
        batch_id=input.batch_id,
        tenant_id=tenant_id,
        data_domain_id=data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        review_validity=input.review_validity,
        summary=summary,
        recommended=feasible,
        assessed_at=assessed_at,
        reason_code="DETERMINISTIC_REFEREE" if feasible else "INFEASIBLE_PAYOFF",
    )
    return RefereeOutput(outcome=outcome, assessment=assessment, reviewed_pending=False)
