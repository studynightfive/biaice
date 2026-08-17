"""Unit tests for recommendation eligibility assessment."""
from __future__ import annotations

import pytest

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.eligibility import (
    GateInputs,
    assert_eligibility_for_recommendation,
    assess_eligibility,
)
from biaice.modules.simulation.domain.models import (
    EligibilityState,
    ReviewValidity,
)


def test_assess_eligibility_returns_eligible_when_all_current() -> None:
    inputs = GateInputs(
        precheck=ReviewValidity.CURRENT,
        readiness=ReviewValidity.CURRENT,
        static_validation=ReviewValidity.CURRENT,
        scenario_assessment=ReviewValidity.CURRENT,
        condition=ReviewValidity.CURRENT,
        risk_acceptance=ReviewValidity.CURRENT,
    )
    result = assess_eligibility(inputs)
    assert result.state == EligibilityState.ELIGIBLE
    assert result.blocked_reason_codes == ()


def test_assess_eligibility_returns_indeterminate_on_unknown() -> None:
    inputs = GateInputs(
        precheck=ReviewValidity.CURRENT,
        readiness=ReviewValidity.UNKNOWN,
        static_validation=ReviewValidity.CURRENT,
        scenario_assessment=ReviewValidity.CURRENT,
        condition=ReviewValidity.CURRENT,
        risk_acceptance=ReviewValidity.CURRENT,
    )
    result = assess_eligibility(inputs)
    assert result.state == EligibilityState.INDETERMINATE
    assert "READINESS_UNKNOWN" in result.blocked_reason_codes


def test_assess_eligibility_returns_ineligible_on_expired() -> None:
    inputs = GateInputs(
        precheck=ReviewValidity.CURRENT,
        readiness=ReviewValidity.CURRENT,
        static_validation=ReviewValidity.CURRENT,
        scenario_assessment=ReviewValidity.CURRENT,
        condition=ReviewValidity.EXPIRED,
        risk_acceptance=ReviewValidity.CURRENT,
    )
    result = assess_eligibility(inputs)
    assert result.state == EligibilityState.INELIGIBLE
    assert "CONDITION_EXPIRED" in result.blocked_reason_codes


def test_assess_eligibility_returns_ineligible_on_invalidated() -> None:
    inputs = GateInputs(
        precheck=ReviewValidity.CURRENT,
        readiness=ReviewValidity.CURRENT,
        static_validation=ReviewValidity.CURRENT,
        scenario_assessment=ReviewValidity.INVALIDATED,
        condition=ReviewValidity.CURRENT,
        risk_acceptance=ReviewValidity.CURRENT,
    )
    result = assess_eligibility(inputs)
    assert result.state == EligibilityState.INELIGIBLE
    assert "SCENARIO_ASSESSMENT_INVALIDATED" in result.blocked_reason_codes


def test_assert_eligibility_for_recommendation_blocks_indeterminate() -> None:
    inputs = GateInputs(
        precheck=ReviewValidity.CURRENT,
        readiness=ReviewValidity.UNKNOWN,
        static_validation=ReviewValidity.CURRENT,
        scenario_assessment=ReviewValidity.CURRENT,
        condition=ReviewValidity.CURRENT,
        risk_acceptance=ReviewValidity.CURRENT,
    )
    result = assess_eligibility(inputs)
    with pytest.raises(BiaiceError) as error:
        assert_eligibility_for_recommendation(result)
    assert error.value.code == "ELIGIBILITY_INPUT_UNKNOWN"
