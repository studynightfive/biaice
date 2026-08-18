"""Recommendation eligibility assessment.

Aggregates the precheck, readiness, static, scenario, condition and risk
acceptance gate verdicts. The assessor is fail-closed: if any input reports
UNKNOWN / EXPIRED / INVALIDATED the eligibility is INDETERMINATE and a
recommendation MUST NOT be ELIGIBLE. The mapping mirrors the public docs:

    precheck           -> precheck:read
    readiness          -> readiness:read
    static validation  -> simulation:batch:read
    scenario assessment-> simulation:optimization:run
    condition          -> simulation:eligibility:assess
    risk acceptance    -> risk-acceptance:read
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    EligibilityState,
    ReviewValidity,
)


@dataclass(frozen=True, slots=True)
class GateInputs:
    precheck: ReviewValidity
    readiness: ReviewValidity
    static_validation: ReviewValidity
    scenario_assessment: ReviewValidity
    condition: ReviewValidity
    risk_acceptance: ReviewValidity

    def as_mapping(self) -> Mapping[str, ReviewValidity]:
        return {
            "precheck": self.precheck,
            "readiness": self.readiness,
            "static_validation": self.static_validation,
            "scenario_assessment": self.scenario_assessment,
            "condition": self.condition,
            "risk_acceptance": self.risk_acceptance,
        }


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    state: EligibilityState
    blocked_reason_codes: tuple[str, ...]
    upstream_validity: Mapping[str, ReviewValidity]


def assess_eligibility(inputs: GateInputs) -> EligibilityResult:
    """Return the eligibility verdict; never ELIGIBLE while an input is not CURRENT."""
    mapping = inputs.as_mapping()
    blocked: list[str] = []
    indeterminate = False
    for gate, validity in mapping.items():
        if validity == ReviewValidity.INVALIDATED:
            blocked.append(f"{gate.upper()}_INVALIDATED")
        elif validity == ReviewValidity.EXPIRED:
            blocked.append(f"{gate.upper()}_EXPIRED")
        elif validity == ReviewValidity.UNKNOWN:
            indeterminate = True
            blocked.append(f"{gate.upper()}_UNKNOWN")
    if blocked and not indeterminate:
        return EligibilityResult(
            state=EligibilityState.INELIGIBLE,
            blocked_reason_codes=tuple(blocked),
            upstream_validity=mapping,
        )
    if indeterminate:
        return EligibilityResult(
            state=EligibilityState.INDETERMINATE,
            blocked_reason_codes=tuple(blocked),
            upstream_validity=mapping,
        )
    return EligibilityResult(
        state=EligibilityState.ELIGIBLE,
        blocked_reason_codes=(),
        upstream_validity=mapping,
    )


def assert_eligibility_for_recommendation(result: EligibilityResult) -> None:
    if result.state != EligibilityState.ELIGIBLE:
        raise BiaiceError(
            "ELIGIBILITY_INPUT_UNKNOWN",
            detail=(
                "上游输入未全部 CURRENT，不得出具推荐结论 / Upstream inputs are not all "
                f"CURRENT; cannot issue a recommendation. State={result.state.value}, "
                f"blocked_reason_codes={list(result.blocked_reason_codes)}."
            ),
        )


def block_codes_for_logging(result: EligibilityResult) -> tuple[str, ...]:
    return result.blocked_reason_codes
