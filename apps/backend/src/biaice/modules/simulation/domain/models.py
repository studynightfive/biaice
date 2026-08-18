"""FR-06/07/08/09a immutable simulation domain models and enumerations.

All models inherit :class:`FrozenModel` (frozen=True, extra="forbid"); the
application layer must reconstruct aggregates for any change. Decimal monetary
fields use the string-only `DecimalStr` pattern; the type system forbids
binary float for any contract field.

Every persisted aggregate carries the mandatory multi-tenant projection:
    tenant_id / data_domain_id / project_id / decision_unit_id / version_id
and the create/freeze triple:
    created_at / created_by / frozen_at / frozen_by
so that audit, scope and invalidation services have a single source of truth.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Final
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DECIMAL_STR_PATTERN: Final[str] = r"^-?\d+(\.\d+)?$"
DECIMAL_REGEX: Final[re.Pattern[str]] = re.compile(DECIMAL_STR_PATTERN)
HASH_PATTERN: Final[str] = r"^[a-f0-9]{64}$"


def validate_decimal_str(value: str) -> str:
    """Reject binary float, NaN, infinity and trailing garbage for monetary fields."""
    if not isinstance(value, str):
        raise TypeError("DecimalStr fields must be string-typed; binary float is forbidden")
    if not DECIMAL_REGEX.fullmatch(value):
        raise ValueError(f"DecimalStr must match {DECIMAL_REGEX.pattern!r}; received {value!r}")
    return value


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DecimalStr(FrozenModel):
    """Decimal-as-string envelope with strict pattern validation."""

    value: str = Field(pattern=DECIMAL_STR_PATTERN)

    @classmethod
    def from_decimal(cls, amount: Decimal) -> "DecimalStr":
        text = format(amount, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return cls(value=text or "0")

    @classmethod
    def coerce(cls, value: Any) -> "DecimalStr":
        if isinstance(value, DecimalStr):
            return value
        if isinstance(value, Decimal):
            return cls.from_decimal(value)
        if isinstance(value, str):
            validate_decimal_str(value)
            return cls(value=value)
        raise TypeError(f"Cannot coerce {type(value).__name__} into DecimalStr")


class BaselineState(StrEnum):
    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


class SearchSpaceState(StrEnum):
    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


class ScenarioSetState(StrEnum):
    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


class ScenarioKind(StrEnum):
    """Search-space and evaluation scenarios must be mutually exclusive sets."""

    SEARCH = "SEARCH"
    EVALUATION = "EVALUATION"
    STRESS = "STRESS"


class BatchState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    INDETERMINATE = "INDETERMINATE"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    CANCELLED = "CANCELLED"


class OptimizationState(StrEnum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"
    FINALIZED = "FINALIZED"


class PlanState(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    INVALIDATED = "INVALIDATED"


class EligibilityState(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    INDETERMINATE = "INDETERMINATE"


class SnapshotState(StrEnum):
    DRAFT = "DRAFT"
    LOCKED = "LOCKED"


class AwardMode(StrEnum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"
    NONE = "NONE"


class ReviewValidity(StrEnum):
    CURRENT = "CURRENT"
    UNKNOWN = "UNKNOWN"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class ObjectiveKind(StrEnum):
    COST_MIN = "COST_MIN"
    MARGIN_MAX = "MARGIN_MAX"
    COVERAGE_MAX = "COVERAGE_MAX"
    RISK_MIN = "RISK_MIN"


class StressAxis(StrEnum):
    PRICE_BAND = "PRICE_BAND"
    TIMING = "TIMING"
    COMPLIANCE = "COMPLIANCE"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    UNIT_FAILURE = "UNIT_FAILURE"


class ReviewReference(FrozenModel):
    reference_id: UUID
    reference_type: str
    reference_version_id: UUID
    content_hash: str = Field(pattern=HASH_PATTERN)
    captured_at: datetime


class ManifestItem(FrozenModel):
    item_id: UUID
    upstream_type: str
    upstream_id: UUID
    upstream_version_id: UUID
    upstream_content_hash: str = Field(pattern=HASH_PATTERN)
    dependency_type: str
    recorded_at: datetime


class InputManifest(FrozenModel):
    manifest_id: UUID
    manifest_hash: str = Field(pattern=HASH_PATTERN)
    items: tuple[ManifestItem, ...] = Field(min_length=1)


class DecisionBaseline(FrozenModel):
    baseline_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    manifest: InputManifest
    state: BaselineState
    frozen_at: datetime | None
    frozen_by: UUID | None
    created_at: datetime
    created_by: UUID
    superseded_at: datetime | None = None
    superseded_by: UUID | None = None
    invalidated_at: datetime | None = None
    invalidated_by: UUID | None = None

    @model_validator(mode="after")
    def frozen_state_requires_frozen_metadata(self) -> "DecisionBaseline":
        if self.state in {BaselineState.FROZEN, BaselineState.SUPERSEDED}:
            if self.frozen_at is None or self.frozen_by is None:
                raise ValueError(
                    "Frozen baselines must record frozen_at and frozen_by "
                    "/ 决策基线 FROZEN 状态必须记录 frozen_at 与 frozen_by."
                )
        return self


class CandidateSearchSpace(FrozenModel):
    search_space_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    baseline_version_id: UUID
    description: str = Field(min_length=1, max_length=400)
    state: SearchSpaceState
    dimension_axes: tuple[str, ...] = Field(min_length=1)
    candidate_count_lower_bound: int = Field(ge=1)
    created_at: datetime
    created_by: UUID
    frozen_at: datetime | None
    frozen_by: UUID | None


class ScenarioSetMember(FrozenModel):
    scenario_id: UUID
    scenario_kind: ScenarioKind
    weight: DecimalStr
    label: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] = Field(default_factory=dict)


class ScenarioSet(FrozenModel):
    scenario_set_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    baseline_version_id: UUID
    search_space_version_id: UUID
    evaluation_space_version_id: UUID | None
    stress_axes: tuple[StressAxis, ...]
    state: ScenarioSetState
    members: tuple[ScenarioSetMember, ...] = Field(min_length=1)
    created_at: datetime
    created_by: UUID
    frozen_at: datetime | None
    frozen_by: UUID | None

    @field_validator("members")
    @classmethod
    def scenario_sets_must_be_non_empty(
        cls, value: tuple[ScenarioSetMember, ...]
    ) -> tuple[ScenarioSetMember, ...]:
        if not value:
            raise ValueError("scenario set must contain at least one scenario")
        return value


class SimulationBatch(FrozenModel):
    batch_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    baseline_version_id: UUID
    scenario_set_version_id: UUID
    award_mode: AwardMode
    state: BatchState
    policy_threshold: DecimalStr
    candidate_count: int = Field(ge=0)
    progress_percent: int = Field(default=0, ge=0, le=100)
    requested_by: UUID
    created_at: datetime
    last_updated_at: datetime
    job_id: UUID | None = None
    failure_reason_code: str | None = None


class SimulationCandidate(FrozenModel):
    candidate_id: UUID
    batch_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    label: str = Field(min_length=1, max_length=160)
    parameters: dict[str, Any]
    expected_cost: DecimalStr
    expected_margin: DecimalStr
    created_at: datetime


class StaticValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"


class StaticCandidateValidation(FrozenModel):
    validation_id: UUID
    candidate_id: UUID
    batch_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    status: StaticValidationStatus
    rule_codes: tuple[str, ...] = Field(default_factory=tuple)
    assessed_at: datetime
    detail: str | None = None


class ScenarioOutcome(FrozenModel):
    outcome_id: UUID
    candidate_id: UUID
    scenario_id: UUID
    batch_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    feasible: bool
    expected_payoff: DecimalStr
    p_win: DecimalStr
    evaluated_at: datetime
    review_validity: ReviewValidity
    detail: str | None = None


class ScenarioStrategyAssessment(FrozenModel):
    assessment_id: UUID
    candidate_id: UUID
    scenario_id: UUID
    batch_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    review_validity: ReviewValidity
    summary: str
    recommended: bool
    assessed_at: datetime
    reason_code: str = Field(min_length=3, max_length=120)


class StressTestAssessment(FrozenModel):
    assessment_id: UUID
    run_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    axis: StressAxis
    passed: bool
    detail: str
    assessed_at: datetime
    stress_weight: DecimalStr


class StrategyPlanMember(FrozenModel):
    candidate_id: UUID
    linkage: str = Field(default="complete")
    weight: DecimalStr


class StrategyPlan(FrozenModel):
    plan_id: UUID
    run_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    state: PlanState
    award_mode: AwardMode
    objective_kind: ObjectiveKind
    members: tuple[StrategyPlanMember, ...] = Field(min_length=1, max_length=4)
    p_minus: DecimalStr
    p_plus: DecimalStr
    coverage: DecimalStr
    created_at: datetime
    published_at: datetime | None
    invalidated_at: datetime | None
    invalidated_by: UUID | None = None
    published_by: UUID | None = None
    linked_run_version_id: UUID


class MergeAssessment(FrozenModel):
    merge_id: UUID
    run_id: UUID
    plan_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    linkage: str
    tau_b: DecimalStr
    tau_m: DecimalStr
    accepted: bool
    blocked_reason_code: str | None
    assessed_at: datetime


class OptimizationRun(FrozenModel):
    run_id: UUID
    batch_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    state: OptimizationState
    award_mode: AwardMode
    objective_kind: ObjectiveKind
    policy_threshold: DecimalStr
    progress_percent: int = Field(default=0, ge=0, le=100)
    requested_by: UUID
    created_at: datetime
    finalized_at: datetime | None
    invalidated_at: datetime | None
    invalidated_by: UUID | None = None


class RecommendationEligibility(FrozenModel):
    eligibility_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    state: EligibilityState
    blocked_reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    upstream_validity: dict[str, ReviewValidity] = Field(default_factory=dict)
    baseline_version_id: UUID
    snapshot_version_id: UUID | None = None
    assessed_at: datetime
    assessed_by: UUID


class SimulationAssessmentSnapshot(FrozenModel):
    snapshot_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    state: SnapshotState
    watermark: str
    payload_hash: str = Field(pattern=HASH_PATTERN)
    payload: dict[str, Any]
    created_at: datetime
    created_by: UUID
    locked_at: datetime | None = None
    locked_by: UUID | None = None


SHADOW_PILOT_LOCKED_WATERMARK: Final[str] = "SHADOW_PILOT_LOCKED"


def new_uuid() -> UUID:
    return uuid4()
