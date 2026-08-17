"""FR-02 immutable domain objects and state machines.

Upload sessions are resumable and expire at read time. Source documents follow
quarantine → scan → review → released. Parse jobs persist progress for polling;
document links inherit project files into units without copying blobs.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHA256_PATTERN = r"^[a-f0-9]{64}$"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DocumentKind(StrEnum):
    TENDER = "TENDER"
    COMPANY = "COMPANY"
    COMPETITOR = "COMPETITOR"
    MARKET = "MARKET"


class DocumentStatus(StrEnum):
    QUARANTINED = "QUARANTINED"
    SCAN_PASSED = "SCAN_PASSED"
    SCAN_FAILED = "SCAN_FAILED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RELEASED = "RELEASED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class ScanResult(StrEnum):
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    ERROR = "ERROR"


class ParseStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ParseRetryable(StrEnum):
    YES = "YES"
    NO_FORMAT_UNSUPPORTED = "NO_FORMAT_UNSUPPORTED"
    NO_CORRUPT = "NO_CORRUPT"
    NO_PASSWORD_PROTECTED = "NO_PASSWORD_PROTECTED"
    NO_MANUAL_ENTRY_REQUIRED = "NO_MANUAL_ENTRY_REQUIRED"


class DocumentMimeCategory(StrEnum):
    PDF = "PDF"
    DOCX = "DOCX"
    XLSX = "XLSX"
    IMAGE = "IMAGE"
    ARCHIVE = "ARCHIVE"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


class DerivedAssetKind(StrEnum):
    OCR_TEXT = "OCR_TEXT"
    PAGE_IMAGE = "PAGE_IMAGE"
    PAGE_SLICE = "PAGE_SLICE"
    EMBEDDING = "EMBEDDING"
    INDEX = "INDEX"
    EXTRACTED_CONTENT = "EXTRACTED_CONTENT"
    CACHE = "CACHE"
    PROMPT = "PROMPT"
    MODEL_RESPONSE = "MODEL_RESPONSE"
    EXPORT = "EXPORT"
    BACKUP = "BACKUP"


class UploadSessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class UploadNextAction(StrEnum):
    UPLOAD_CHUNK = "UPLOAD_CHUNK"
    COMPLETE = "COMPLETE"
    NONE = "NONE"


class UploadChunkInfo(FrozenModel):
    part_number: int = Field(ge=1)
    offset: int = Field(ge=0)
    size_bytes: int = Field(gt=0)
    expected_sha256: str = Field(pattern=SHA256_PATTERN)
    received_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    received_at: datetime | None = None


class UploadSession(FrozenModel):
    session_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    kind: DocumentKind
    filename: str = Field(min_length=1, max_length=500)
    file_size_bytes: int = Field(gt=0)
    content_type: str = Field(max_length=100)
    mime_category: DocumentMimeCategory
    declared_sha256: str = Field(pattern=SHA256_PATTERN)
    chunk_size_bytes: int = Field(gt=0)
    total_parts: int = Field(ge=1)
    received_parts: tuple[UploadChunkInfo, ...] = ()
    status: UploadSessionStatus
    final_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    final_size_bytes: int | None = Field(default=None, ge=0)
    quarantine_key: str | None = None
    document_id: UUID | None = None
    created_by: UUID
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def scope_must_be_project_or_unit(self) -> "UploadSession":
        if self.project_id is None and self.decision_unit_id is None:
            raise ValueError("upload session requires a project or decision-unit scope")
        return self


class SourceDocument(FrozenModel):
    document_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    kind: DocumentKind
    name: str = Field(min_length=1, max_length=500)
    storage_key: str
    storage_locator_hash: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(gt=0)
    content_hash: str = Field(pattern=SHA256_PATTERN)
    declared_content_type: str
    sniffed_content_type: str
    mime_category: DocumentMimeCategory
    scan_result: ScanResult
    scan_signature_version: str | None = None
    scan_details: str | None = None
    status: DocumentStatus
    quarantined_at: datetime | None = None
    scan_completed_at: datetime | None = None
    released_at: datetime | None = None
    uploaded_by: UUID
    uploaded_at: datetime
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    released_by: UUID | None = None
    upload_session_id: UUID
    source_filename: str | None = None

    @model_validator(mode="after")
    def released_requires_clean_scan(self) -> "SourceDocument":
        if self.status is DocumentStatus.RELEASED:
            if self.scan_result is not ScanResult.CLEAN:
                raise ValueError("released document must have passed scan")
            if self.released_by is None or self.released_at is None:
                raise ValueError("released document requires release metadata")
            if self.released_by == self.uploaded_by:
                raise ValueError("uploader cannot release their own document")
        return self


class ParseJob(FrozenModel):
    job_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    document_id: UUID
    document_version_id: UUID | None = None
    status: ParseStatus
    stage: str | None = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    retryable: ParseRetryable | None = None
    failure_reason_code: str | None = None
    failure_detail: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    attempt: int = Field(default=1, ge=1)
    max_attempts: int = Field(default=3, ge=1)
    derived_asset_ids: tuple[UUID, ...] = ()
    created_by: UUID


class DerivedAsset(FrozenModel):
    asset_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    source_document_id: UUID
    source_document_version_id: UUID | None = None
    parse_job_id: UUID | None = None
    kind: DerivedAssetKind
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    storage_key: str
    storage_locator_hash: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int | None = Field(default=None, ge=0)
    content_hash: str | None = Field(default=None, pattern=SHA256_PATTERN)
    mime_type: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    fragment_ref: str = Field(min_length=1, max_length=500)
    created_at: datetime


class DocumentLinkRelation(StrEnum):
    INHERITED = "INHERITED"
    OVERRIDE = "OVERRIDE"


class DocumentLinkConflictState(StrEnum):
    NONE = "NONE"
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class DocumentLink(FrozenModel):
    link_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    source_document_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    relation: DocumentLinkRelation
    priority: int = Field(default=0, ge=0)
    conflict_state: DocumentLinkConflictState = DocumentLinkConflictState.NONE
    confirmation_reason: str | None = None
    confirmed_by: UUID | None = None
    created_by: UUID
    created_at: datetime
    detached_at: datetime | None = None


class ReleasedDocumentView(FrozenModel):
    """Read-only projection for members 2/4/5. Bodies are never included."""

    document_id: UUID
    content_hash: str = Field(pattern=SHA256_PATTERN)
    status: DocumentStatus
    parse_status: ParseStatus | None = None
    fragment_refs: tuple[str, ...] = ()
    reviewed_by: UUID | None = None
    released_by: UUID | None = None
    uploaded_at: datetime


def downloadable_statuses() -> frozenset[DocumentStatus]:
    return frozenset(
        {
            DocumentStatus.SCAN_PASSED,
            DocumentStatus.UNDER_REVIEW,
            DocumentStatus.RELEASED,
        }
    )


def parsable_statuses() -> frozenset[DocumentStatus]:
    return downloadable_statuses()


def effective_upload_session(item: UploadSession, *, now: datetime) -> UploadSession:
    if item.status is UploadSessionStatus.ACTIVE and now >= item.expires_at:
        return item.model_copy(update={"status": UploadSessionStatus.EXPIRED})
    return item


def missing_part_numbers(item: UploadSession) -> tuple[int, ...]:
    received = {part.part_number for part in item.received_parts}
    return tuple(part for part in range(1, item.total_parts + 1) if part not in received)


def next_upload_action(item: UploadSession) -> UploadNextAction:
    if item.status is not UploadSessionStatus.ACTIVE:
        return UploadNextAction.NONE
    if missing_part_numbers(item):
        return UploadNextAction.UPLOAD_CHUNK
    return UploadNextAction.COMPLETE
