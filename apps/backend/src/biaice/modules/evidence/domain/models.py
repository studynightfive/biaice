"""Immutable FR-03 evidence, match, response, precheck and condition models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LifecycleState(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class ReviewState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    NOT_REQUIRED = "NOT_REQUIRED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class ValidityState(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class RetentionState(StrEnum):
    RETAIN = "RETAIN"
    DISPOSITION_DUE = "DISPOSITION_DUE"
    DISPOSITION_RUNNING = "DISPOSITION_RUNNING"
    DISPOSED = "DISPOSED"


class MatchState(StrEnum):
    SATISFIED = "SATISFIED"
    PARTIAL = "PARTIAL"
    UNSATISFIED = "UNSATISFIED"
    UNKNOWN = "UNKNOWN"


class EvidenceCategory(StrEnum):
    QUALIFICATION = "QUALIFICATION"
    CASE = "CASE"
    PERSONNEL = "PERSONNEL"
    TECHNICAL = "TECHNICAL"
    SERVICE = "SERVICE"
    COMMITMENT = "COMMITMENT"


class PrecheckDecision(StrEnum):
    PASS = "PASS"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class ConditionState(StrEnum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    WAIVED = "WAIVED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class BlockingStage(StrEnum):
    COMPUTE = "COMPUTE"
    FREEZE = "FREEZE"
    APPROVAL = "APPROVAL"
    AUTHORIZATION = "AUTHORIZATION"
    SUBMISSION = "SUBMISSION"


class OrthogonalState(FrozenModel):
    lifecycle_state: LifecycleState
    review_state: ReviewState
    validity_state: ValidityState
    retention_state: RetentionState = RetentionState.RETAIN
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    superseded_by_id: UUID | None = None


class Requirement(OrthogonalState):
    requirement_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    rule_clause_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=4000)
    mandatory: bool
    source_document_id: UUID | None = None
    source_page: str | None = Field(default=None, max_length=40)
    source_section: str | None = Field(default=None, max_length=120)
    etag: str = Field(min_length=66, max_length=66)
    created_at: datetime
    created_by: UUID
    published_at: datetime | None = None
    published_by: UUID | None = None


class CompanyEvidence(OrthogonalState):
    evidence_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    category: EvidenceCategory
    subject: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=400)
    source_document_id: UUID | None = None
    fragment_ref: str | None = Field(default=None, max_length=200)
    content_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    valid_from: datetime
    valid_to: datetime
    created_at: datetime
    created_by: UUID
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None
    published_at: datetime | None = None
    published_by: UUID | None = None
    revoked_at: datetime | None = None
    revoked_by: UUID | None = None
    revocation_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validity_window_ordered(self) -> "CompanyEvidence":
        if self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be later than valid_from")
        return self


class EvidenceMatch(FrozenModel):
    match_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    requirement_id: UUID
    evidence_id: UUID | None = None
    state: MatchState
    rationale: str = Field(min_length=1, max_length=2000)
    original_etag: str | None = Field(default=None, max_length=66)
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None
    created_at: datetime
    created_by: UUID
    validity_state: ValidityState = ValidityState.CURRENT


class CompanyResponseProfile(OrthogonalState):
    profile_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    qualification_preparation: str = Field(min_length=1, max_length=4000)
    technical_response: str = Field(min_length=1, max_length=4000)
    service_response: str = Field(min_length=1, max_length=4000)
    objective_non_price_inputs: dict[str, str] = Field(default_factory=dict)
    subjective_variable_intervals: dict[str, str] = Field(default_factory=dict)
    evidence_ids: tuple[UUID, ...] = ()
    valid_from: datetime
    valid_to: datetime
    created_at: datetime
    created_by: UUID
    published_at: datetime | None = None
    published_by: UUID | None = None

    @model_validator(mode="after")
    def validity_window_ordered(self) -> "CompanyResponseProfile":
        if self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be later than valid_from")
        return self


class PrecheckCheck(FrozenModel):
    code: str
    passed: bool | None
    reason_code: str


class PrecheckAssessment(FrozenModel):
    precheck_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    decision: PrecheckDecision
    validity_state: ValidityState
    rules_available: bool | None
    subject_qualification: MatchState
    substantive_response: MatchState
    evidence_coverage: MatchState
    deadline_closure: bool | None
    unmapped_mandatory_count: int = Field(ge=0)
    condition_ids: tuple[UUID, ...] = ()
    checks: tuple[PrecheckCheck, ...] = ()
    created_at: datetime
    created_by: UUID


class ConditionRequirement(FrozenModel):
    condition_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=2000)
    state: ConditionState
    owner_id: UUID
    independent_reviewer_id: UUID
    evidence_id: UUID | None = None
    due_at: datetime
    blocking_stage: BlockingStage
    created_at: datetime
    created_by: UUID
    closed_at: datetime | None = None
    closed_by: UUID | None = None
    close_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def maker_checker_independent(self) -> "ConditionRequirement":
        if self.owner_id == self.independent_reviewer_id:
            raise ValueError("condition owner and independent reviewer must differ")
        return self


class FormalInputAllowed(FrozenModel):
    allowed: bool
    failed_predicates: tuple[str, ...] = ()


def formal_input_allowed(item: OrthogonalState, *, now: datetime) -> FormalInputAllowed:
    failed: list[str] = []
    if item.lifecycle_state is not LifecycleState.PUBLISHED:
        failed.append("lifecycle_not_published")
    if item.review_state not in {ReviewState.APPROVED, ReviewState.NOT_REQUIRED}:
        failed.append("review_not_approved")
    if item.validity_state is not ValidityState.CURRENT:
        failed.append("validity_not_current")
    if item.retention_state is not RetentionState.RETAIN:
        failed.append("retention_not_retain")
    if item.effective_from is not None and now < item.effective_from:
        failed.append("not_yet_effective")
    if item.effective_to is not None and now >= item.effective_to:
        failed.append("effective_window_ended")
    if item.superseded_by_id is not None:
        failed.append("superseded")
    return FormalInputAllowed(allowed=not failed, failed_predicates=tuple(failed))


def condition_is_blocking(item: ConditionRequirement, *, now: datetime) -> bool:
    if item.state is ConditionState.EXPIRED:
        return True
    if item.state is ConditionState.FAILED:
        return True
    if item.state is ConditionState.OPEN and now >= item.due_at:
        return True
    return item.state is ConditionState.OPEN
