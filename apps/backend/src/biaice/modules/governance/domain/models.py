"""FR-11 immutable domain objects and state machines."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ScopedObjectRef(FrozenModel):
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    object_type: str
    object_id: UUID
    version_id: UUID | None = None


class DependencyType(StrEnum):
    COMPUTATIONAL = "COMPUTATIONAL"
    EVIDENTIAL = "EVIDENTIAL"
    POLICY = "POLICY"
    AUTHORIZATION = "AUTHORIZATION"
    PRESENTATIONAL = "PRESENTATIONAL"


class UpstreamChangeType(StrEnum):
    DRAFT_CREATED = "DRAFT_CREATED"
    SNAPSHOT_FROZEN = "SNAPSHOT_FROZEN"
    PUBLISH_EFFECTIVE = "PUBLISH_EFFECTIVE"
    REVOKE = "REVOKE"
    DELETE = "DELETE"
    RETENTION_EXPIRED = "RETENTION_EXPIRED"
    AUTHORIZATION_WITHDRAWN = "AUTHORIZATION_WITHDRAWN"
    PURPOSE_ENDED = "PURPOSE_ENDED"
    PROVIDER_POLICY_EXPIRED = "PROVIDER_POLICY_EXPIRED"
    MODEL_POLICY_EFFECTIVE = "MODEL_POLICY_EFFECTIVE"


class InvalidationEffect(StrEnum):
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class InputManifestItem(FrozenModel):
    manifest_item_id: UUID
    downstream: ScopedObjectRef
    upstream_type: str
    upstream_id: UUID
    upstream_version_id: UUID
    upstream_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    dependency_type: DependencyType
    affected_fields: frozenset[str] = Field(min_length=1)
    recorded_at: datetime


class DataLineageEdge(FrozenModel):
    edge_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    upstream_type: str
    upstream_id: UUID
    upstream_version_id: UUID
    downstream_type: str
    downstream_id: UUID
    downstream_version_id: UUID | None = None
    dependency_type: DependencyType
    affected_fields: frozenset[str] = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def forbid_self_edge(self) -> "DataLineageEdge":
        if self.upstream_type == self.downstream_type and self.upstream_id == self.downstream_id:
            raise ValueError("lineage self-edges are forbidden")
        return self


class InvalidationEvent(FrozenModel):
    invalidation_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    source_event_id: UUID
    lineage_edge_id: UUID
    downstream_type: str
    downstream_id: UUID
    downstream_version_id: UUID | None = None
    effect: InvalidationEffect
    reason_code: str
    occurred_at: datetime
    idempotency_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class SupersessionEvent(FrozenModel):
    supersession_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    object_type: str
    superseded_version_id: UUID
    successor_version_id: UUID
    reason_code: str
    occurred_at: datetime
    actor_id: UUID

    @model_validator(mode="after")
    def versions_must_differ(self) -> "SupersessionEvent":
        if self.superseded_version_id == self.successor_version_id:
            raise ValueError("a version cannot supersede itself")
        return self


class RetentionAction(StrEnum):
    DELETE = "DELETE"
    CRYPTO_ERASE = "CRYPTO_ERASE"
    ARCHIVE = "ARCHIVE"
    REVIEW = "REVIEW"


class RetentionJobState(StrEnum):
    SCHEDULED = "SCHEDULED"
    FORMAL_USE_BLOCKED = "FORMAL_USE_BLOCKED"
    WAITING_FOR_HOLD_RELEASE = "WAITING_FOR_HOLD_RELEASE"
    DISPOSITION_RUNNING = "DISPOSITION_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    ESCALATED = "ESCALATED"


class RetentionDispositionJob(FrozenModel):
    retention_job_id: UUID
    target: ScopedObjectRef
    retention_expires_at: datetime
    action: RetentionAction
    state: RetentionJobState
    formal_use_blocked_at: datetime | None = None
    legal_hold_count: int = Field(default=0, ge=0)
    attempt: int = Field(default=0, ge=0)
    next_attempt_at: datetime | None = None


class LegalHoldState(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class LegalHoldRecord(FrozenModel):
    legal_hold_id: UUID
    target: ScopedObjectRef
    state: LegalHoldState
    reason_code: str
    authority_reference_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    placed_by: UUID
    placed_at: datetime
    released_by: UUID | None = None
    release_checked_by: UUID | None = None
    released_at: datetime | None = None

    @model_validator(mode="after")
    def enforce_release_dual_control(self) -> "LegalHoldRecord":
        if self.state == LegalHoldState.RELEASED:
            if not self.released_by or not self.release_checked_by or not self.released_at:
                raise ValueError("released holds require maker, independent checker and timestamp")
            if self.released_by == self.release_checked_by:
                raise ValueError("hold release maker and checker must differ")
        return self


class ReplicaKind(StrEnum):
    DATABASE = "DATABASE"
    OBJECT_STORAGE = "OBJECT_STORAGE"
    SEARCH_INDEX = "SEARCH_INDEX"
    VECTOR_INDEX = "VECTOR_INDEX"
    CACHE = "CACHE"
    TEMPORARY_FILE = "TEMPORARY_FILE"
    PROVIDER_EXTERNAL = "PROVIDER_EXTERNAL"
    BACKUP = "BACKUP"
    AUDIT_DERIVED = "AUDIT_DERIVED"


class AdapterOwner(StrEnum):
    MEMBER_1_GOVERNANCE = "MEMBER_1_GOVERNANCE"
    MEMBER_3_LOCAL_REPLICA = "MEMBER_3_LOCAL_REPLICA"
    MEMBER_5_PROVIDER_REPLICA = "MEMBER_5_PROVIDER_REPLICA"


class ReplicaLocation(FrozenModel):
    replica_id: UUID
    target: ScopedObjectRef
    kind: ReplicaKind
    adapter_name: str
    adapter_owner: AdapterOwner
    locator_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    required_for_completion: bool = True
    deletion_sla_seconds: int = Field(gt=0)
    retention_expires_at: datetime | None = None


class DeletionJobState(StrEnum):
    REQUESTED = "REQUESTED"
    LOGICAL_ACCESS_BLOCKED = "LOGICAL_ACCESS_BLOCKED"
    WAITING_FOR_HOLD_RELEASE = "WAITING_FOR_HOLD_RELEASE"
    DISPATCHING = "DISPATCHING"
    WAITING_FOR_RECEIPTS = "WAITING_FOR_RECEIPTS"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"


class ReceiptOutcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    UNSUPPORTED = "UNSUPPORTED"


class DeletionReceipt(FrozenModel):
    receipt_id: UUID
    deletion_job_id: UUID
    replica_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    adapter_name: str
    outcome: ReceiptOutcome
    attempted_at: datetime
    completed_at: datetime | None = None
    evidence_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    adapter_signature: str
    verified: bool = False
    stable_error_code: str | None = None
    retry_after: datetime | None = None

    @property
    def satisfies_completion(self) -> bool:
        return (
            self.outcome == ReceiptOutcome.SUCCEEDED
            and self.verified
            and self.completed_at is not None
        )


class DeletionJob(FrozenModel):
    deletion_job_id: UUID
    target: ScopedObjectRef
    state: DeletionJobState
    reason_code: str
    requested_by: UUID
    requested_at: datetime
    idempotency_key: str
    logical_access_blocked_at: datetime | None = None
    required_replica_ids: frozenset[UUID] = Field(default_factory=frozenset)
    receipts: tuple[DeletionReceipt, ...] = ()
    legal_hold_count: int = Field(default=0, ge=0)
    attempt: int = Field(default=0, ge=0)
    completed_at: datetime | None = None
    tombstone_id: UUID | None = None

    @model_validator(mode="after")
    def completion_is_evidence_bound(self) -> "DeletionJob":
        if self.state == DeletionJobState.COMPLETED:
            if self.logical_access_blocked_at is None or self.legal_hold_count:
                raise ValueError("completed deletion requires blocked access and no active hold")
            successful = {
                receipt.replica_id for receipt in self.receipts if receipt.satisfies_completion
            }
            if not self.required_replica_ids.issubset(successful):
                raise ValueError("completed deletion requires every required verified receipt")
            if self.completed_at is None or self.tombstone_id is None:
                raise ValueError("completed deletion requires completion time and tombstone")
        return self


class DeletionReplicaCommand(FrozenModel):
    command_id: UUID
    deletion_job_id: UUID
    replica: ReplicaLocation
    issued_at: datetime
    deadline_at: datetime
    attempt: int = Field(ge=1)
    idempotency_key: str


class TombstoneRecord(FrozenModel):
    tombstone_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    deleted_object_type: str
    deleted_object_id: UUID
    deleted_version_id: UUID | None = None
    deletion_job_id: UUID
    deleted_at: datetime
    reason_code: str
    minimal_reference_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    # No source text, personal data, object name, secret, prompt or cost fields.
