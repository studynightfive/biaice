"""Unit tests for the deterministic scenario referee."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from biaice.modules.simulation.domain.models import ReviewValidity
from biaice.modules.simulation.domain.referee import RefereeInput, evaluate_scenario

TENANT = uuid4()
DOMAIN = uuid4()
UNIT = uuid4()
NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def test_referee_is_deterministic_for_same_inputs() -> None:
    candidate_id = uuid4()
    scenario_id = uuid4()
    batch_id = uuid4()
    inp = RefereeInput(
        candidate_id=candidate_id,
        scenario_id=scenario_id,
        batch_id=batch_id,
        baseline_manifest_hash="a" * 64,
        scenario_kind="EVALUATION",
        candidate_parameters={"x": 1},
        scenario_parameters={"y": 2},
        feasibility_threshold=Decimal("0"),
        pay_off_lower=Decimal("0"),
        pay_off_upper=Decimal("1"),
        seed=42,
        review_validity=ReviewValidity.CURRENT,
    )
    first = evaluate_scenario(
        inp,
        assessed_at=NOW,
        tenant_id=TENANT,
        data_domain_id=DOMAIN,
        project_id=None,
        decision_unit_id=UNIT,
    )
    second = evaluate_scenario(
        inp,
        assessed_at=NOW,
        tenant_id=TENANT,
        data_domain_id=DOMAIN,
        project_id=None,
        decision_unit_id=UNIT,
    )
    assert first.outcome.expected_payoff == second.outcome.expected_payoff
    assert first.outcome.p_win == second.outcome.p_win
    assert first.assessment.recommended == second.assessment.recommended


def test_referee_excludes_non_current_reviews() -> None:
    inp = RefereeInput(
        candidate_id=uuid4(),
        scenario_id=uuid4(),
        batch_id=uuid4(),
        baseline_manifest_hash="a" * 64,
        scenario_kind="EVALUATION",
        candidate_parameters={},
        scenario_parameters={},
        feasibility_threshold=Decimal("0"),
        pay_off_lower=Decimal("0"),
        pay_off_upper=Decimal("1"),
        seed=1,
        review_validity=ReviewValidity.UNKNOWN,
    )
    result = evaluate_scenario(
        inp,
        assessed_at=NOW,
        tenant_id=TENANT,
        data_domain_id=DOMAIN,
        project_id=None,
        decision_unit_id=UNIT,
    )
    assert result.reviewed_pending is True
    assert result.outcome.feasible is False
    assert "not CURRENT" in (result.outcome.detail or "")


def test_referee_separates_recommended_and_not_recommended() -> None:
    inp = RefereeInput(
        candidate_id=uuid4(),
        scenario_id=uuid4(),
        batch_id=uuid4(),
        baseline_manifest_hash="a" * 64,
        scenario_kind="EVALUATION",
        candidate_parameters={},
        scenario_parameters={},
        feasibility_threshold=Decimal("0.99"),  # unreachable; pay_off_upper=1.0 still <=
        pay_off_lower=Decimal("0"),
        pay_off_upper=Decimal("0.5"),  # forces infeasible
        seed=7,
        review_validity=ReviewValidity.CURRENT,
    )
    result = evaluate_scenario(
        inp,
        assessed_at=NOW,
        tenant_id=TENANT,
        data_domain_id=DOMAIN,
        project_id=None,
        decision_unit_id=UNIT,
    )
    assert result.outcome.feasible is False
    assert result.assessment.recommended is False
    assert result.assessment.reason_code == "INFEASIBLE_PAYOFF"
