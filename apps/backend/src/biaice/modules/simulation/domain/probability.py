"""Probability utilities for FR-07/08.

All functions are pure and treat UNDEFINED (zero denominator or insufficient
coverage) as a first-class signal: `is_undefined` lets the service layer
mark a strategy plan UNDEFINED instead of fabricating a number.

Coverage and Monte-Carlo intervals follow the canonical N_eff = sum(p_i *
(1 - p_i)) for Bernoulli samples; q_award_normalize projects the q-award
weights so they sum to 1 across multi-award scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping, Sequence
from uuid import UUID

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import DecimalStr


@dataclass(frozen=True, slots=True)
class CoverageReport:
    total_scenarios: int
    denominator_scenarios: int
    coverage: DecimalStr
    denominator_below_threshold: bool
    threshold: DecimalStr

    @property
    def is_undefined(self) -> bool:
        return self.denominator_below_threshold


@dataclass(frozen=True, slots=True)
class MonteCarloInterval:
    mean: DecimalStr
    lower: DecimalStr
    upper: DecimalStr
    n_eff: DecimalStr
    z: float


def p_minus(outcomes: Sequence[tuple[Decimal, Decimal]]) -> Decimal:
    """Sum(weight * payoff) over the feasibility window; weights are scenario weights."""
    if not outcomes:
        raise BiaiceError(
            "DENOMINATOR_BELOW_THRESHOLD",
            detail=("p_minus 需要至少一个评估结果 / p_minus needs at least one evaluated outcome."),
        )
    total = Decimal("0")
    for weight, payoff in outcomes:
        total += weight * payoff
    return total


def p_plus(outcomes: Sequence[tuple[Decimal, Decimal]]) -> Decimal:
    """Best-case payoff under the feasibility envelope (sum of (weight * upper bound)).

    The referee supplies one outcome per (candidate, scenario); the service
    layer pairs each p_win with the scenario weight to obtain the upper
    envelope.
    """
    if not outcomes:
        raise BiaiceError(
            "DENOMINATOR_BELOW_THRESHOLD",
            detail=("p_plus 需要至少一个评估结果 / p_plus needs at least one evaluated outcome."),
        )
    upper = Decimal("0")
    for weight, payoff in outcomes:
        upper += weight * payoff
    return upper


def coverage(
    *,
    total_scenarios: int,
    denominator_scenarios: int,
    threshold: DecimalStr,
) -> CoverageReport:
    """Return the coverage fraction and the UNDEFINED flag when below threshold."""
    if total_scenarios <= 0:
        raise BiaiceError(
            "COVERAGE_BELOW_THRESHOLD",
            detail=("场景集合为空 / Scenario set is empty; coverage is undefined."),
        )
    if denominator_scenarios <= 0:
        report = CoverageReport(
            total_scenarios=total_scenarios,
            denominator_scenarios=0,
            coverage=DecimalStr.from_decimal(Decimal("0")),
            denominator_below_threshold=True,
            threshold=threshold,
        )
        return report
    fraction = Decimal(denominator_scenarios) / Decimal(total_scenarios)
    threshold_value = Decimal(threshold.value)
    below = fraction < threshold_value
    return CoverageReport(
        total_scenarios=total_scenarios,
        denominator_scenarios=denominator_scenarios,
        coverage=DecimalStr.from_decimal(fraction),
        denominator_below_threshold=below,
        threshold=threshold,
    )


def n_eff(p_wins: Iterable[Decimal]) -> Decimal:
    """Effective sample size under Bernoulli observations."""
    total = Decimal("0")
    for p in p_wins:
        total += p * (Decimal("1") - p)
    return total


def mc_ci(
    *,
    p_wins: Sequence[Decimal],
    z: float = 1.96,
) -> MonteCarloInterval:
    """Return Monte-Carlo mean + interval using N_eff = sum(p*(1-p))."""
    if not p_wins:
        raise BiaiceError(
            "DENOMINATOR_BELOW_THRESHOLD",
            detail=(
                "蒙特卡洛置信区间需要至少一个样本 / Monte-Carlo CI requires at least one sample."
            ),
        )
    n = Decimal(len(p_wins))
    mean = sum(p_wins, Decimal("0")) / n
    eff = n_eff(p_wins)
    if eff <= 0:
        half_width = Decimal("0")
    else:
        half_width = (Decimal(str(z)) * mean * (Decimal("1") - mean) / eff).sqrt()
    return MonteCarloInterval(
        mean=DecimalStr.from_decimal(mean.quantize(Decimal("0.0001"))),
        lower=DecimalStr.from_decimal((mean - half_width).quantize(Decimal("0.0001"))),
        upper=DecimalStr.from_decimal((mean + half_width).quantize(Decimal("0.0001"))),
        n_eff=DecimalStr.from_decimal(eff.quantize(Decimal("0.0001"))),
        z=z,
    )


def q_award_normalize(weights: Mapping[UUID, Decimal]) -> dict[UUID, Decimal]:
    """Normalize q-award weights so they sum to 1 across multi-award scenarios."""
    total = sum(weights.values(), Decimal("0"))
    if total <= 0:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=("q_award 权重总和必须为正数 / q_award weights must sum to a positive value."),
        )
    return {key: value / total for key, value in weights.items()}


def is_undefined(report: CoverageReport) -> bool:
    """True when the report flags the denominator as below threshold or zero."""
    return report.denominator_below_threshold
