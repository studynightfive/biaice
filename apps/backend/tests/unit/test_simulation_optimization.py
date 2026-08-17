"""Unit tests for candidate generation, ranking and selection."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from biaice.modules.simulation.domain.models import (
    AwardMode,
    DecimalStr,
    ObjectiveKind,
    SimulationCandidate,
)
from biaice.modules.simulation.domain.optimization import (
    CandidateBlueprint,
    generate_candidates,
    rank_candidates,
    select_objective_candidates,
)

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def _candidate(margin: str, cost: str = "1") -> SimulationCandidate:
    return SimulationCandidate(
        candidate_id=uuid4(),
        batch_id=uuid4(),
        version_id=uuid4(),
        tenant_id=uuid4(),
        data_domain_id=uuid4(),
        project_id=None,
        decision_unit_id=uuid4(),
        label="x",
        parameters={"a": 1},
        expected_cost=DecimalStr(value=cost),
        expected_margin=DecimalStr(value=margin),
        created_at=NOW,
    )


def test_generate_candidates_returns_empty_when_no_blueprints() -> None:
    candidates = generate_candidates(
        batch_id=uuid4(),
        version_id=uuid4(),
        tenant_id=uuid4(),
        data_domain_id=uuid4(),
        project_id=None,
        decision_unit_id=uuid4(),
        blueprints=(),
        created_at=NOW,
    )
    assert candidates == ()


def test_generate_candidates_assigns_unique_ids() -> None:
    candidates = generate_candidates(
        batch_id=uuid4(),
        version_id=uuid4(),
        tenant_id=uuid4(),
        data_domain_id=uuid4(),
        project_id=None,
        decision_unit_id=uuid4(),
        blueprints=(
            CandidateBlueprint(label="a", parameters={}, expected_cost=Decimal("1"), expected_margin=Decimal("10")),
            CandidateBlueprint(label="b", parameters={}, expected_cost=Decimal("2"), expected_margin=Decimal("20")),
        ),
        created_at=NOW,
    )
    assert len(candidates) == 2
    assert len({c.candidate_id for c in candidates}) == 2


def test_rank_candidates_orders_by_margin_max() -> None:
    a = _candidate(margin="1")
    b = _candidate(margin="3")
    c = _candidate(margin="2")
    ranked = rank_candidates([a, b, c], objective_kind=ObjectiveKind.MARGIN_MAX)
    assert [r.candidate.candidate_id for r in ranked] == [b.candidate_id, c.candidate_id, a.candidate_id]


def test_select_objective_candidates_caps_at_four_for_multi() -> None:
    candidates = tuple(_candidate(margin=str(i)) for i in range(6))
    ranked = rank_candidates(candidates, objective_kind=ObjectiveKind.MARGIN_MAX)
    plan = select_objective_candidates(
        ranked=ranked,
        policy_threshold=DecimalStr(value="0"),
        award_mode=AwardMode.MULTI,
        objective_kind=ObjectiveKind.MARGIN_MAX,
    )
    assert len(plan.selected) == 4


def test_select_objective_candidates_single_returns_one() -> None:
    candidates = tuple(_candidate(margin=str(i)) for i in range(3))
    ranked = rank_candidates(candidates, objective_kind=ObjectiveKind.MARGIN_MAX)
    plan = select_objective_candidates(
        ranked=ranked,
        policy_threshold=DecimalStr(value="0"),
        award_mode=AwardMode.SINGLE,
        objective_kind=ObjectiveKind.MARGIN_MAX,
    )
    assert len(plan.selected) == 1


def test_select_objective_candidates_returns_empty_below_threshold() -> None:
    candidates = tuple(_candidate(margin="1") for _ in range(3))
    ranked = rank_candidates(candidates, objective_kind=ObjectiveKind.MARGIN_MAX)
    plan = select_objective_candidates(
        ranked=ranked,
        policy_threshold=DecimalStr(value="100"),
        award_mode=AwardMode.MULTI,
        objective_kind=ObjectiveKind.MARGIN_MAX,
    )
    assert plan.selected == ()
