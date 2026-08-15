"""Scenario freezing and search/eval independence validation.

Probability and stress scenarios belong to disjoint sets; evaluation scenarios
must never re-use an axis already covered by stress axes (which are forbidden
from the probability denominator). Search and evaluation spaces must originate
from distinct `candidate_search_space` versions; sharing one space across
phases makes coverage indistinguishable from bias and is rejected with
SCENARIO_SET_INVALID.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable
from uuid import UUID

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    ScenarioKind,
    ScenarioSet,
    ScenarioSetMember,
    ScenarioSetState,
    SearchSpaceState,
    StressAxis,
)


def freeze_scenarios(
    *,
    set_id: UUID,
    version_id: UUID,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID,
    baseline_version_id: UUID,
    search_space_version_id: UUID,
    evaluation_space_version_id: UUID | None,
    members: Iterable[ScenarioSetMember],
    stress_axes: Iterable[StressAxis],
    search_space_state: SearchSpaceState,
    created_at,
    created_by: UUID,
    now,
) -> ScenarioSet:
    """Return a frozen scenario set in state FROZEN.

    Validation:
        * at least one SEARCH and one EVALUATION member;
        * no STRESS members in the probability set (stresses are axes, not weights);
        * weights are normalized (sum ≈ 1) within 1e-9;
        * search and evaluation spaces must be different version_ids when the
          evaluation set is explicit.
    """
    members_tuple = tuple(members)
    if not members_tuple:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "场景集至少需要一个成员 / Scenario set must contain at least one member."
            ),
        )

    kinds = Counter(member.scenario_kind for member in members_tuple)
    if kinds.get(ScenarioKind.STRESS, 0) > 0:
        raise BiaiceError(
            "STRESS_AXIS_VIOLATED",
            detail=(
                "压力轴不能进入概率集合 / Stress axes must not enter the probability set; "
                "use run_stress_tests with explicit stress_axes instead."
            ),
        )
    if kinds.get(ScenarioKind.SEARCH, 0) < 1 or kinds.get(ScenarioKind.EVALUATION, 0) < 1:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "场景集必须同时包含 SEARCH 与 EVALUATION / Scenario set must contain at "
                "least one SEARCH and one EVALUATION scenario."
            ),
        )

    weights = [int(member.weight.value.replace(".", "").lstrip("-") or "0") for member in members_tuple]
    total = sum(weights)
    if total <= 0:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "场景权重总和必须为正数 / Sum of scenario weights must be positive."
            ),
        )
    # Normalize to string-friendly DecimalStr via a 4-digit precision.
    weight_total = sum(__decimal(member.weight.value) for member in members_tuple)
    if abs(weight_total - 1) > 1e-9:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                f"场景权重未归一化（总和={weight_total}）/ Scenario weights must sum to 1 "
                f"within 1e-9 tolerance, got {weight_total}."
            ),
        )

    if (
        evaluation_space_version_id is not None
        and evaluation_space_version_id == search_space_version_id
    ):
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "搜索空间与评估空间版本必须不同 / Search and evaluation spaces must originate "
                "from distinct candidate_search_space versions."
            ),
        )

    if search_space_state != SearchSpaceState.FROZEN:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "搜索空间必须先冻结 / Candidate search space must be in FROZEN state before "
                "a scenario set can be assembled."
            ),
        )

    return ScenarioSet(
        scenario_set_id=set_id,
        version_id=version_id,
        tenant_id=tenant_id,
        data_domain_id=data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        baseline_version_id=baseline_version_id,
        search_space_version_id=search_space_version_id,
        evaluation_space_version_id=evaluation_space_version_id,
        stress_axes=tuple(stress_axes),
        state=ScenarioSetState.FROZEN,
        members=members_tuple,
        created_at=created_at,
        created_by=created_by,
        frozen_at=now,
        frozen_by=created_by,
    )


def validate_search_eval_independence(scenario_set: ScenarioSet) -> None:
    """Reject any scenario set that violates the SEARCH/EVALUATION/STRESS split."""
    kinds = Counter(member.scenario_kind for member in scenario_set.members)
    if kinds.get(ScenarioKind.STRESS, 0):
        raise BiaiceError(
            "STRESS_AXIS_VIOLATED",
            detail=(
                "场景集不允许 STRESS 成员 / STRESS members must never appear inside a "
                "frozen scenario set; use stress axes instead."
            ),
        )
    if not (kinds.get(ScenarioKind.SEARCH, 0) and kinds.get(ScenarioKind.EVALUATION, 0)):
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "场景集必须同时包含 SEARCH 与 EVALUATION / Scenario set must contain at "
                "least one SEARCH and one EVALUATION scenario."
            ),
        )
    if scenario_set.evaluation_space_version_id == scenario_set.search_space_version_id:
        raise BiaiceError(
            "SCENARIO_SET_INVALID",
            detail=(
                "搜索与评估空间必须来自不同的 candidate_search_space 版本 / Search and "
                "evaluation spaces must originate from distinct versions."
            ),
        )


def __decimal(value: str):
    from decimal import Decimal
    return Decimal(value)
