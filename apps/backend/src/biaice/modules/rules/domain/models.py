"""Immutable FR-01 scope, regime, rule and compliance models (member 2)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from biaice.core.versioning import VersionMetadata
from biaice.modules.projects.domain.models import ResourceLifecycle, ResourceValidity


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationMethod(StrEnum):
    COMPREHENSIVE_SCORING = "COMPREHENSIVE_SCORING"
    LOWEST_EVALUATED_PRICE = "LOWEST_EVALUATED_PRICE"
    OTHER_UNSUPPORTED = "OTHER_UNSUPPORTED"


class ProcurementMode(StrEnum):
    OPEN_TENDERING = "OPEN_TENDERING"
    INVITED_TENDERING = "INVITED_TENDERING"
    OTHER_UNSUPPORTED = "OTHER_UNSUPPORTED"


class RoundKind(StrEnum):
    SINGLE_ROUND = "SINGLE_ROUND"
    MULTI_ROUND = "MULTI_ROUND"


class ScopeSupport(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    PORTFOLIO_REVIEW_REQUIRED = "PORTFOLIO_REVIEW_REQUIRED"
    MULTI_ROUND_UNSUPPORTED = "MULTI_ROUND_UNSUPPORTED"


class RuleClauseKind(StrEnum):
    QUALIFICATION = "QUALIFICATION"
    SUBSTANTIVE = "SUBSTANTIVE"
    SCORING = "SCORING"
    FORMULA = "FORMULA"
    ROUNDING = "ROUNDING"
    TIE = "TIE"
    CANDIDATE = "CANDIDATE"
    VALID_SUPPLIER_COUNT = "VALID_SUPPLIER_COUNT"
    SAME_BRAND = "SAME_BRAND"
    ABNORMALLY_LOW = "ABNORMALLY_LOW"
    CONTRACT = "CONTRACT"
    SUBMISSION = "SUBMISSION"


class RuleScopeLevel(StrEnum):
    PROJECT = "PROJECT"
    DECISION_UNIT = "DECISION_UNIT"


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    CONFLICT_REQUIRES_CONFIRMATION = "CONFLICT_REQUIRES_CONFIRMATION"


class ComplianceReviewState(StrEnum):
    OPEN = "OPEN"
    BLOCKING = "BLOCKING"
    ACCEPTED_FOR_SIMULATION = "ACCEPTED_FOR_SIMULATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SourceLocator(FrozenModel):
    document_id: UUID | None = None
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=200)
    excerpt: str | None = Field(default=None, max_length=4000)


class ScopeAssessment(FrozenModel):
    scope_assessment_id: UUID
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    support: ScopeSupport
    round_kind: RoundKind
    cross_lot: bool
    reason_codes: tuple[str, ...] = ()
    source: SourceLocator | None = None
    applicability: str | None = Field(default=None, max_length=2000)
    lifecycle_state: ResourceLifecycle
    validity_state: ResourceValidity
    version: VersionMetadata
    effective_from: datetime | None = None
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None


class ApplicableRegime(FrozenModel):
    applicable_regime_id: UUID
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    regime_name: str = Field(min_length=1, max_length=200)
    procurement_mode: ProcurementMode
    evaluation_method: EvaluationMethod
    round_kind: RoundKind
    source: SourceLocator | None = None
    lifecycle_state: ResourceLifecycle
    validity_state: ResourceValidity
    version: VersionMetadata
    effective_from: datetime | None = None
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None


class RuleSet(FrozenModel):
    rule_set_id: UUID
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    title: str = Field(min_length=1, max_length=200)
    scope_level: RuleScopeLevel
    lifecycle_state: ResourceLifecycle
    validity_state: ResourceValidity
    version: VersionMetadata
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None


class RuleClause(FrozenModel):
    rule_clause_id: UUID
    rule_set_id: UUID
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    kind: RuleClauseKind
    coverage_key: str = Field(min_length=1, max_length=120)
    priority: int = Field(ge=1, le=1000)
    original_text: str = Field(min_length=1, max_length=8000)
    structured_expression: str | None = Field(default=None, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    source: SourceLocator | None = None
    supersedes_clause_id: UUID | None = None
    lifecycle_state: ResourceLifecycle
    validity_state: ResourceValidity
    version: VersionMetadata
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None


class ComplianceReview(FrozenModel):
    compliance_review_id: UUID
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    state: ComplianceReviewState
    finding: str = Field(min_length=1, max_length=4000)
    blocking: bool
    version: VersionMetadata


class CrossLotConstraint(FrozenModel):
    cross_lot_constraint_id: UUID
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    related_unit_ids: tuple[UUID, ...]
    description: str = Field(min_length=1, max_length=2000)
    confirmed: bool
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None
    version: VersionMetadata


class RuleResolution(FrozenModel):
    coverage_key: str
    status: ResolutionStatus
    winning_clause_id: UUID | None = None
    conflicting_clause_ids: tuple[UUID, ...] = ()
    detail: str
