"""SQLAlchemy 2 FR-11 tables. RLS policies are installed by forward migrations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from biaice.core.db import Base, TenantScopedMixin


class InputManifestItemRow(Base, TenantScopedMixin):
    __tablename__ = "input_manifest_item"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "downstream_version_id",
            "upstream_version_id",
            "dependency_type",
            name="uq_manifest_actual_dependency",
        ),
    )

    manifest_item_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    downstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    downstream_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    downstream_version_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    upstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    upstream_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    upstream_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    upstream_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(30), nullable=False)
    affected_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DataLineageEdgeRow(Base, TenantScopedMixin):
    __tablename__ = "data_lineage_edge"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "upstream_version_id",
            "downstream_id",
            "downstream_version_id",
            "dependency_type",
            name="uq_lineage_actual_dependency",
        ),
    )

    edge_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    upstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    upstream_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    upstream_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    downstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    downstream_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    downstream_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, nullable=True, index=True
    )
    dependency_type: Mapped[str] = mapped_column(String(30), nullable=False)
    affected_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class InvalidationEventRow(Base, TenantScopedMixin):
    __tablename__ = "invalidation_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "idempotency_fingerprint",
            name="uq_invalidation_idempotency",
        ),
    )

    invalidation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    lineage_edge_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    downstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    downstream_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    downstream_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    effect: Mapped[str] = mapped_column(String(30), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    idempotency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class SupersessionEventRow(Base, TenantScopedMixin):
    __tablename__ = "supersession_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "object_type",
            "superseded_version_id",
            "successor_version_id",
            name="uq_supersession_pair",
        ),
    )

    supersession_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    superseded_version_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    successor_version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class RetentionDispositionJobRow(Base, TenantScopedMixin):
    __tablename__ = "retention_disposition_job"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "target_type",
            "target_id",
            "target_version_id",
            "retention_expires_at",
            name="uq_retention_due_target",
        ),
    )

    retention_job_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    target_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    formal_use_blocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    legal_hold_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LegalHoldRecordRow(Base, TenantScopedMixin):
    __tablename__ = "legal_hold_record"

    legal_hold_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    target_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    authority_reference_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    placed_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    release_checked_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LegalHoldOverrideRow(Base, TenantScopedMixin):
    __tablename__ = "legal_hold_override"

    override_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    legal_hold_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    checked_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DeletionJobRow(Base, TenantScopedMixin):
    __tablename__ = "deletion_job"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "idempotency_key",
            name="uq_deletion_scope_idempotency",
        ),
    )

    deletion_job_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    target_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    logical_access_blocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    required_replica_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String(36)), nullable=False, default=list
    )
    legal_hold_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tombstone_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class DeletionReceiptRow(Base, TenantScopedMixin):
    __tablename__ = "deletion_receipt"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "deletion_job_id",
            "replica_id",
            "evidence_hash",
            name="uq_deletion_receipt_evidence",
        ),
    )

    receipt_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    deletion_job_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    replica_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    adapter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_signature: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stable_error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TombstoneRecordRow(Base, TenantScopedMixin):
    __tablename__ = "tombstone_record"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "deletion_job_id",
            name="uq_tombstone_deletion_job",
        ),
    )

    tombstone_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    deleted_object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    deleted_object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    deleted_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    deletion_job_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    minimal_reference_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ReplicaLocationProjectionRow(Base, TenantScopedMixin):
    """Read projection populated by member-owned replica registries."""

    __tablename__ = "replica_location_projection"

    replica_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    target_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    adapter_owner: Mapped[str] = mapped_column(String(60), nullable=False)
    locator_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    required_for_completion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    deletion_sla_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    adapter_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
