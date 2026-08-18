"""Unit tests for probability helpers (FR-07/08)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import DecimalStr
from biaice.modules.simulation.domain.probability import (
    coverage,
    is_undefined,
    mc_ci,
    n_eff,
    p_minus,
    p_plus,
    q_award_normalize,
)


def test_p_minus_and_p_plus_sum_weights() -> None:
    outcomes = [(Decimal("0.4"), Decimal("100")), (Decimal("0.6"), Decimal("50"))]
    assert p_minus(outcomes) == Decimal("70")
    assert p_plus(outcomes) == Decimal("70")


def test_p_minus_requires_outcomes() -> None:
    with pytest.raises(BiaiceError) as error:
        p_minus([])
    assert error.value.code == "DENOMINATOR_BELOW_THRESHOLD"


def test_coverage_reports_undefined_below_threshold() -> None:
    report = coverage(
        total_scenarios=10, denominator_scenarios=2, threshold=DecimalStr(value="0.5")
    )
    assert report.is_undefined
    assert is_undefined(report)
    high = coverage(total_scenarios=10, denominator_scenarios=8, threshold=DecimalStr(value="0.5"))
    assert not high.is_undefined


def test_coverage_zero_denominator_is_undefined() -> None:
    report = coverage(
        total_scenarios=10, denominator_scenarios=0, threshold=DecimalStr(value="0.1")
    )
    assert report.is_undefined


def test_n_eff_matches_bernoulli() -> None:
    p_wins = [Decimal("0.1"), Decimal("0.5"), Decimal("0.9")]
    expected = sum(p * (Decimal("1") - p) for p in p_wins)
    assert abs(n_eff(p_wins) - expected) < Decimal("1e-9")


def test_mc_ci_returns_n_eff_and_bounds() -> None:
    p_wins = [Decimal("0.1"), Decimal("0.5"), Decimal("0.9")]
    interval = mc_ci(p_wins=p_wins, z=1.96)
    assert interval.n_eff.value is not None
    assert interval.lower.value is not None
    assert interval.upper.value is not None


def test_q_award_normalize_sums_to_one() -> None:
    weights = {uuid4(): Decimal("1"), uuid4(): Decimal("3")}
    normalised = q_award_normalize(weights)
    assert sum(normalised.values()) == Decimal("1")


def test_q_award_normalize_rejects_zero_total() -> None:
    weights = {uuid4(): Decimal("0"), uuid4(): Decimal("0")}
    with pytest.raises(BiaiceError):
        q_award_normalize(weights)
