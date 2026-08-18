"""Stress-test runner.

Stress axes are intentionally outside the probability denominator. A stress
test passes only if (a) the candidate survives every hard axis without
violating the linkage rule, and (b) no stress weight bleeds into the
probability set. The runner is pure; the application service is responsible
for persisting the resulting assessments and for surfacing STRESS_AXIS_VIOLATED
when a hard constraint fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    DecimalStr,
    SimulationCandidate,
    StressAxis,
    StressTestAssessment,
    new_uuid,
)


@dataclass(frozen=True, slots=True)
class StressScenario:
    """One hard axis evaluation against one candidate."""

    axis: StressAxis
    feasible: bool
    stress_weight: Decimal
    detail: str


@dataclass(frozen=True, slots=True)
class StressReport:
    run_id: UUID
    assessments: tuple[StressTestAssessment, ...]
    hard_axis_violations: tuple[StressAxis, ...]
    failed_assessment_count: int

    @property
    def passed(self) -> bool:
        return not self.hard_axis_violations


def run_stress_tests(
    *,
    run_id: UUID,
    candidates: Sequence[SimulationCandidate],
    scenarios: Mapping[StressAxis, Iterable[StressScenario]],
    assessed_at,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID,
) -> StressReport:
    """Materialise stress tests; the only side effect is the report itself."""
    assessments: list[StressTestAssessment] = []
    violations: list[StressAxis] = []
    for candidate in candidates:
        for axis, scenarios_for_axis in scenarios.items():
            for scenario in scenarios_for_axis:
                if scenario.axis != axis:
                    raise BiaiceError(
                        "STRESS_AXIS_VIOLATED",
                        detail=(
                            f"stress scenario axis mismatch: expected {axis} got "
                            f"{scenario.axis} for candidate {candidate.candidate_id}."
                        ),
                    )
                if scenario.stress_weight > Decimal("0"):
                    raise BiaiceError(
                        "STRESS_AXIS_VIOLATED",
                        detail=(
                            "stress 轴权重必须为 0；不得进入概率分母 / Stress weights must be "
                            "zero in the probability denominator; do not enter stress axes."
                        ),
                    )
                assessment = StressTestAssessment(
                    assessment_id=new_uuid(),
                    run_id=run_id,
                    tenant_id=tenant_id,
                    data_domain_id=data_domain_id,
                    project_id=project_id,
                    decision_unit_id=decision_unit_id,
                    axis=axis,
                    passed=scenario.feasible,
                    detail=scenario.detail,
                    assessed_at=assessed_at,
                    stress_weight=DecimalStr.from_decimal(scenario.stress_weight),
                )
                assessments.append(assessment)
                if not scenario.feasible:
                    violations.append(axis)
    return StressReport(
        run_id=run_id,
        assessments=tuple(assessments),
        hard_axis_violations=tuple(dict.fromkeys(violations)),
        failed_assessment_count=sum(1 for item in assessments if not item.passed),
    )


def assert_no_stress_axis_in_probability(weights: Mapping[UUID, Decimal]) -> None:
    for axis, weight in weights.items():
        if weight > Decimal("0"):
            raise BiaiceError(
                "STRESS_AXIS_VIOLATED",
                detail=(
                    f"stress axis {axis} must not enter the probability denominator "
                    f"(weight={weight})."
                ),
            )
