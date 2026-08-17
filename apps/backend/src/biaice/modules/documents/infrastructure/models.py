"""FR-02 SQLAlchemy 2 tables."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from biaice.core.db import Base, TenantScopedMixin


class UploadSessionRow(Base, TenantScopedMixin):
    """Chunked upload session for resumable file transfer."""

    __tablename__ = "document_upload_session"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "idempotency_key",
            name="uq_upload_session_idempotency",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    mime_category: Mapped[str] = mapped_column(String(30), nullable=False)
    declared_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    chunk_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    received_parts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    status: Mapped[str] = mapped_column(String(30), nullable=False)

    final_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    final_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    quarantine_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    released_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class SourceDocumentRow(Base, TenantScopedMixin):
    """Source document record after quarantine release."""

    __tablename__ = "source_document"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "upload_session_id",
            name="uq_source_document_session",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    upload_session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)

    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_locator_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    declared_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sniffed_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    mime_category: Mapped[str] = mapped_column(String(30), nullable=False)
    scan_result: Mapped[str] = mapped_column(String(30), nullable=False)
    scan_signature_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scan_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False)
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scan_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    uploaded_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DocumentLifecycleEventRow(Base, TenantScopedMixin):
    """Immutable event record for document lifecycle transitions."""

    __tablename__ = "document_lifecycle_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "event_idempotency_key",
            name="uq_document_lifecycle_idempotency",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    event_idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)

    document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    document_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)

    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    actor_role: Mapped[str | None] = mapped_column(String(100), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    upload_session_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    scan_result: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parse_job_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class ParseJobRow(Base, TenantScopedMixin):
    """Document parsing task."""

    __tablename__ = "document_parse_job"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "idempotency_key",
            name="uq_parse_job_idempotency",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    document_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    retryable: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_reason_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    derived_asset_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid), nullable=False, default=list
    )

    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class DerivedAssetRow(Base, TenantScopedMixin):
    """Asset derived from source document processing."""

    __tablename__ = "document_derived_asset"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "source_document_id",
            "kind",
            "generation",
            name="uq_derived_asset_unique",
        ),
    )

    asset_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    source_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    source_document_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    parse_job_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_locator_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    replica_locations_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    retained_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentReplicaLocationRow(Base, TenantScopedMixin):
    """Replica location for document and derived assets."""

    __tablename__ = "document_replica_location"

    replica_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    target_object_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    target_version_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    adapter_owner: Mapped[str] = mapped_column(String(60), nullable=False)
    locator_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    required_for_completion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deletion_sla_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=86400)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentLinkRow(Base, TenantScopedMixin):
    """Project-to-unit document link without copying blobs."""

    __tablename__ = "document_link"

    link_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_document_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflict_state: Mapped[str] = mapped_column(String(30), nullable=False)
    confirmation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
