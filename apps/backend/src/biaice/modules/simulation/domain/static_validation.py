"""Static candidate validation.

Static validation runs before any scenario work: it checks that the
candidate's parameter payload references existing scope, satisfies the rule
clause set, falls inside the cost envelope, and does not collide with revoked
manual overrides. Failed or INDETERMINATE validations force the batch into
CANDIDATE_ERROR_NOT_RECOVERABLE — they never trigger scenario deletion or
metric inflation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, FrozenSet, Mapping, Sequence

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    DecimalStr,
    SimulationCandidate,
    StaticCandidateValidation,
    StaticValidationStatus,
    new_uuid,
)


@dataclass(frozen=True, slots=True)
class StaticValidationContext:
    """Static rules extracted from the frozen baseline manifest and the simulation batch."""

    rule_codes: FrozenSet[str]
    revoked_overrides: FrozenSet[str]
    cost_upper_bound: DecimalStr
    feasibility_threshold: DecimalStr
    referenced_axes: FrozenSet[str]
    mandatory_fields: FrozenSet[str]


@dataclass(frozen=True, slots=True)
class StaticValidationResult:
    validation: StaticCandidateValidation
    blocking_reason_codes: tuple[str, ...]


def validate_candidate(
    *,
    candidate: SimulationCandidate,
    context: StaticValidationContext,
    assessed_at: datetime,
) -> StaticValidationResult:
    """Return either PASS, FAIL or INDETERMINATE plus the list of blocking codes."""
    blocking: list[str] = []
    params: Mapping[str, Any] = candidate.parameters
    missing = [field for field in context.mandatory_fields if field not in params]
    if missing:
        blocking.append(f"MISSING_FIELDS:{','.join(sorted(missing))}")

    referenced = {str(key) for key in params.keys()}
    if not referenced.issubset(context.referenced_axes):
        blocking.append("UNREFERENCED_AXES")

    rule_codes = set(context.rule_codes)
    violated = sorted(referenced & rule_codes & {"FORBIDDEN", "REVOKED"})
    if violated:
        blocking.append("RULE_VIOLATION:" + ",".join(violated))
    if context.revoked_overrides & referenced:
        blocking.append("REVOKED_OVERRIDE_REFERENCED")

    cost = _decimal(candidate.expected_cost.value)
    upper = _decimal(context.cost_upper_bound.value)
    if cost > upper:
        blocking.append("COST_OVER_BUDGET")

    feasibility = _decimal(context.feasibility_threshold.value)
    margin = _decimal(candidate.expected_margin.value)
    if margin < feasibility:
        blocking.append("MARGIN_BELOW_FEASIBILITY")

    if blocking:
        status = StaticValidationStatus.FAIL
    else:
        status = StaticValidationStatus.PASS

    validation = StaticCandidateValidation(
        validation_id=new_uuid(),
        candidate_id=candidate.candidate_id,
        batch_id=candidate.batch_id,
        tenant_id=candidate.tenant_id,
        data_domain_id=candidate.data_domain_id,
        project_id=candidate.project_id,
        decision_unit_id=candidate.decision_unit_id,
        status=status,
        rule_codes=tuple(blocking),
        assessed_at=assessed_at,
        detail=(
            None
            if status == StaticValidationStatus.PASS
            else "静态校验未通过 / Static validation did not pass: " + "; ".join(blocking)
        ),
    )
    return StaticValidationResult(validation=validation, blocking_reason_codes=tuple(blocking))


def assert_validation_passed(results: Sequence[StaticValidationResult]) -> None:
    """Raise CANDIDATE_ERROR_NOT_RECOVERABLE if any candidate was not PASS."""
    failed = [
        result for result in results if result.validation.status != StaticValidationStatus.PASS
    ]
    if failed:
        first = failed[0]
        raise BiaiceError(
            "CANDIDATE_ERROR_NOT_RECOVERABLE",
            detail=(
                "候选级静态校验未通过，不得删除场景或人为膨胀指标 / Candidate-level static "
                f"validation failed: candidate_id={first.validation.candidate_id}, "
                f"reason_codes={list(first.validation.rule_codes)}."
            ),
        )


def _decimal(value: str):
    from decimal import Decimal

    return Decimal(value)
