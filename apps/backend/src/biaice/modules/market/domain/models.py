"""FR-05 and FR-12 market/privacy domain models owned by member 5."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "api_key",
        "credential",
        "credential_plaintext",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "raw_prompt",
        "prompt",
        "model_response",
        "response_body",
    }
)


def _reject_sensitive_payload(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            canonical = re.sub(r"(?<!^)(?=[A-Z])", "_", key).replace("-", "_").lower()
            if canonical in SENSITIVE_PAYLOAD_KEYS:
                raise ValueError(f"sensitive field is forbidden: {path}.{key}")
            _reject_sensitive_payload(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_payload(nested, f"{path}[{index}]")


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProcessingRecordState(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"


class ProcessingRecord(FrozenModel):
    processing_record_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    external_source_id: UUID | None = None
    source_uri: str | None = Field(default=None, max_length=1024)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    legal_basis_ref: str = Field(min_length=1, max_length=200)
    expires_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    state: ProcessingRecordState = ProcessingRecordState.DRAFT
    state_reason: str | None = Field(default=None, max_length=1000)
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    actor_id: UUID


class MarketResourceState(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    REVOKED = "REVOKED"


class MarketResourceRecord(FrozenModel):
    """Generic member-5 resource slice record for non-FR-12 specific endpoints."""

    resource_id: UUID
    version_id: UUID
    resource: str
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    actor_id: UUID
    state: MarketResourceState = MarketResourceState.DRAFT
    payload: dict[str, Any] = Field(default_factory=dict)
    related_ids: dict[str, UUID] = Field(default_factory=dict)
    last_action: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("payload")
    @classmethod
    def payload_must_not_contain_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        _reject_sensitive_payload(value)
        return value


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    PERSONAL = "PERSONAL"
    SENSITIVE_PERSONAL = "SENSITIVE_PERSONAL"


class SourceReviewState(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    QUARANTINED = "QUARANTINED"
    EXPIRED = "EXPIRED"


class PublicationState(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    QUARANTINED = "QUARANTINED"


class MarketReadiness(StrEnum):
    PROBABILISTIC = "PROBABILISTIC"
    PRESSURE_ONLY = "PRESSURE_ONLY"


class Competitor(FrozenModel):
    competitor_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    canonical_subject_key: str = Field(min_length=3, max_length=200)
    legal_name: str = Field(min_length=1, max_length=300)
    aliases: tuple[str, ...] = ()
    actor_id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    archive_reason: str | None = Field(default=None, max_length=1000)

    @field_validator("canonical_subject_key")
    @classmethod
    def normalize_subject_key(cls, value: str) -> str:
        normalized = "".join(value.casefold().split())
        if len(normalized) < 3:
            raise ValueError("canonical subject key is too short after normalization")
        return normalized


class CompetitorSource(FrozenModel):
    source_id: UUID
    version_id: UUID = Field(default_factory=uuid4)
    competitor_id: UUID | None
    tenant_id: UUID
    data_domain_id: UUID
    source_uri: str = Field(min_length=1, max_length=1024)
    source_type: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=120)
    legal_basis_ref: str = Field(min_length=1, max_length=200)
    retention_expires_at: datetime
    data_classification: DataClassification
    evidence_refs: tuple[str, ...] = ()
    notes: str | None = Field(default=None, max_length=2000)
    subject_resolved: bool = False
    review_state: SourceReviewState = SourceReviewState.DRAFT
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    quarantine_reason: str | None = None
    actor_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def review_is_evidence_bound(self) -> "CompetitorSource":
        if self.review_state == SourceReviewState.REVIEWED:
            if not self.subject_resolved or self.competitor_id is None:
                raise ValueError("reviewed competitor source requires a resolved subject")
            if self.reviewed_by is None or self.reviewed_at is None:
                raise ValueError("reviewed competitor source requires reviewer evidence")
        if self.review_state == SourceReviewState.QUARANTINED and not self.quarantine_reason:
            raise ValueError("quarantined source requires a reason")
        return self

    @property
    def formally_usable(self) -> bool:
        return (
            self.review_state == SourceReviewState.REVIEWED
            and self.subject_resolved
            and self.retention_expires_at > datetime.now(timezone.utc)
        )


class CompetitorProfile(FrozenModel):
    profile_id: UUID
    version_id: UUID = Field(default_factory=uuid4)
    competitor_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    source_ids: tuple[UUID, ...] = Field(min_length=1)
    participation_assumptions: dict[str, float] = Field(default_factory=dict)
    bid_assumptions: dict[str, float] = Field(default_factory=dict)
    potential_response_states: tuple[str, ...] = ()
    subjective_variables: dict[str, float] = Field(default_factory=dict)
    validity_assumptions: tuple[str, ...] = ()
    coverage_notes: str = Field(min_length=1, max_length=2000)
    bias_notes: str = Field(min_length=1, max_length=2000)
    drift_notes: str = Field(min_length=1, max_length=2000)
    data_quality: str = Field(min_length=1, max_length=120)
    state: PublicationState = PublicationState.DRAFT
    actor_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    published_at: datetime | None = None


class MarketPriorVersion(FrozenModel):
    market_prior_id: UUID
    version_id: UUID = Field(default_factory=uuid4)
    decision_unit_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    purpose: str = Field(min_length=1, max_length=120)
    legal_basis_ref: str = Field(min_length=1, max_length=200)
    valid_from: datetime
    expires_at: datetime
    state: PublicationState = PublicationState.DRAFT
    distribution: dict[str, float]
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    actor_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    published_at: datetime | None = None

    @field_validator("distribution")
    @classmethod
    def distribution_is_valid(cls, value: dict[str, float]) -> dict[str, float]:
        if not value or any(probability < 0 for probability in value.values()):
            raise ValueError("market prior probabilities must be non-negative")
        if abs(sum(value.values()) - 1.0) > 1e-9:
            raise ValueError("market prior probabilities must sum to one")
        return value

    @model_validator(mode="after")
    def validity_period_is_ordered(self) -> "MarketPriorVersion":
        if self.expires_at <= self.valid_from:
            raise ValueError("market prior expiry must be after valid_from")
        return self


class UnknownEntrantProfileVersion(FrozenModel):
    profile_id: UUID
    version_id: UUID = Field(default_factory=uuid4)
    decision_unit_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    excluded_subject_keys: frozenset[str]
    count_distribution: dict[int, float]
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    expires_at: datetime
    state: PublicationState = PublicationState.DRAFT
    actor_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    published_at: datetime | None = None

    @field_validator("count_distribution")
    @classmethod
    def count_distribution_is_valid(cls, value: dict[int, float]) -> dict[int, float]:
        if not value or any(count < 0 or probability < 0 for count, probability in value.items()):
            raise ValueError("unknown entrant count distribution must be non-negative")
        if abs(sum(value.values()) - 1.0) > 1e-9:
            raise ValueError("unknown entrant count probabilities must sum to one")
        return value


class SubjectDeduplicationState(StrEnum):
    SUCCEEDED = "SUCCEEDED"


class SubjectDeduplicationRun(FrozenModel):
    run_id: UUID
    decision_unit_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    state: SubjectDeduplicationState = SubjectDeduplicationState.SUCCEEDED
    input_subject_keys: tuple[str, ...] = Field(min_length=1)
    canonical_subject_keys: tuple[str, ...] = Field(min_length=1)
    duplicate_groups: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    named_subject_matches: frozenset[str] = frozenset()
    actor_id: UUID
    created_at: datetime
    completed_at: datetime


class JointParticipationScenario(FrozenModel):
    named_competitor_ids: frozenset[UUID] = frozenset()
    unknown_entrant_count: int = Field(ge=0)
    probability: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def scenario_has_market_competition(self) -> "JointParticipationScenario":
        if not self.named_competitor_ids and self.unknown_entrant_count == 0:
            raise ValueError("a formal scenario cannot assume the bidder is the only entrant")
        return self


class JointParticipationDistribution(FrozenModel):
    version_id: UUID
    decision_unit_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    scenarios: tuple[JointParticipationScenario, ...] = Field(min_length=1)
    subject_deduplication_run_id: UUID
    created_at: datetime

    @model_validator(mode="after")
    def probabilities_sum_to_one(self) -> "JointParticipationDistribution":
        if abs(sum(item.probability for item in self.scenarios) - 1.0) > 1e-9:
            raise ValueError("joint participation probabilities must sum to one")
        return self
