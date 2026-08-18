"""Strategy-plan merge with chain-link blocking.

The merger only accepts complete-linkage merges across the same (run_id,
objective_kind, baseline_version). It refuses to chain adjacent candidates
across tau_b or tau_m thresholds because doing so silently re-defines the
batch's feasibility window.

Hard rules:
    * linkage MUST equal "complete";
    * tau_b and tau_m are decimal-string distances, both must be >= the
      minimum gap (0.0 by default) and <= the maximum gap (1.0 by default);
    * any (candidate_i, candidate_{i+1}) pair that crosses a tau threshold
      blocks the merge with PLAN_MERGE_BLOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    DecimalStr,
    MergeAssessment,
    StrategyPlanMember,
    new_uuid,
)


@dataclass(frozen=True, slots=True)
class MergeRequest:
    plan_id: UUID
    run_id: UUID
    baseline_version_id: UUID
    candidate_ids: tuple[UUID, ...]
    linkage: str
    tau_b: DecimalStr
    tau_m: DecimalStr


def merge_assessments(
    request: MergeRequest,
    *,
    assessed_at,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID,
) -> MergeAssessment:
    """Validate the merge request and return the persisted assessment record."""
    if request.linkage != "complete":
        raise BiaiceError(
            "PLAN_MERGE_BLOCKED",
            detail=(
                "仅允许 complete-linkage 合并 / Only complete-linkage merges are "
                f"accepted; received linkage={request.linkage!r}."
            ),
        )
    if len(request.candidate_ids) < 1 or len(request.candidate_ids) > 4:
        raise BiaiceError(
            "PLAN_MERGE_BLOCKED",
            detail=(
                "每个方案至多包含 4 个候选，且至少 1 个 / Each plan must contain between 1 "
                f"and 4 candidates; received {len(request.candidate_ids)}."
            ),
        )

    tau_b = Decimal(request.tau_b.value)
    tau_m = Decimal(request.tau_m.value)
    if tau_b < Decimal("0") or tau_b > Decimal("1"):
        raise BiaiceError(
            "PLAN_MERGE_BLOCKED",
            detail=(
                f"tau_b 必须在 [0, 1] 之间 / tau_b must be in [0, 1]; received {tau_b}."
            ),
        )
    if tau_m < Decimal("0") or tau_m > Decimal("1"):
        raise BiaiceError(
            "PLAN_MERGE_BLOCKED",
            detail=(
                f"tau_m 必须在 [0, 1] 之间 / tau_m must be in [0, 1]; received {tau_m}."
            ),
        )

    seen: set[UUID] = set()
    duplicates = []
    chain_blocked = False
    previous: UUID | None = None
    for candidate in request.candidate_ids:
        if candidate in seen:
            duplicates.append(str(candidate))
        seen.add(candidate)
        if previous is not None and candidate != previous:
            if (tau_b + tau_m) > Decimal("1"):
                chain_blocked = True
        previous = candidate
    if duplicates:
        raise BiaiceError(
            "PLAN_MERGE_BLOCKED",
            detail=(
                "方案候选必须互不重复 / Strategy plan candidates must be unique; "
                f"duplicates={duplicates}."
            ),
        )

    blocked_reason: str | None = None
    if chain_blocked:
        blocked_reason = "TAU_CHAIN_BLOCK"

    return MergeAssessment(
        merge_id=new_uuid(),
        run_id=request.run_id,
        plan_id=request.plan_id,
        tenant_id=tenant_id,
        data_domain_id=data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        linkage=request.linkage,
        tau_b=request.tau_b,
        tau_m=request.tau_m,
        accepted=blocked_reason is None,
        blocked_reason_code=blocked_reason,
        assessed_at=assessed_at,
    )


def assert_merge_accepted(assessment: MergeAssessment) -> None:
    if not assessment.accepted:
        raise BiaiceError(
            "PLAN_MERGE_BLOCKED",
            detail=(
                "方案合并被阻断 / Plan merge blocked; reason_code="
                f"{assessment.blocked_reason_code}; linkage must be complete and tau "
                "gates must not chain adjacent candidates."
            ),
        )


def as_plan_members(assessment: MergeAssessment, candidates: Sequence[UUID]) -> tuple[StrategyPlanMember, ...]:
    return tuple(
        StrategyPlanMember(candidate_id=candidate_id, linkage=assessment.linkage, weight=DecimalStr.from_decimal(Decimal("0.25")))
        for candidate_id in candidates
    )
