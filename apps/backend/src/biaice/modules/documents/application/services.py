"""Application services for member-3 FR-02 upload, scan and release."""

from __future__ import annotations

import hashlib
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any, Mapping
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.modules.documents.application.ports import (
    DocumentReadPort,
    LegalHoldQueryPort,
    NoLegalHolds,
)
from biaice.modules.documents.application.repository import InMemoryDocumentsRepository
from biaice.modules.documents.domain.models import (
    DerivedAsset,
    DerivedAssetKind,
    DocumentKind,
    DocumentLink,
    DocumentLinkConflictState,
    DocumentLinkRelation,
    DocumentMimeCategory,
    DocumentStatus,
    ParseJob,
    ParseRetryable,
    ParseStatus,
    ReleasedDocumentView,
    ScanResult,
    SourceDocument,
    UploadChunkInfo,
    UploadSession,
    UploadSessionStatus,
    downloadable_statuses,
    effective_upload_session,
    missing_part_numbers,
    parsable_statuses,
)
from biaice.modules.documents.infrastructure.parsers import parse_document
from biaice.modules.documents.infrastructure.scanner import scan_bytes
from biaice.modules.governance.domain.models import (
    AdapterOwner,
    ReplicaKind,
    ReplicaLocation,
    ScopedObjectRef,
)

MEMBER3_ADAPTER_NAME = "member3-local"
DELETION_SLA_SECONDS = 86400

ALLOWED_EXTENSIONS = {
    ".pdf": DocumentMimeCategory.PDF,
    ".docx": DocumentMimeCategory.DOCX,
    ".xlsx": DocumentMimeCategory.XLSX,
    ".png": DocumentMimeCategory.IMAGE,
    ".jpg": DocumentMimeCategory.IMAGE,
    ".jpeg": DocumentMimeCategory.IMAGE,
    ".tif": DocumentMimeCategory.IMAGE,
    ".tiff": DocumentMimeCategory.IMAGE,
    ".webp": DocumentMimeCategory.IMAGE,
    ".zip": DocumentMimeCategory.ARCHIVE,
}
BLOCKED_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".msi",
    ".dll",
    ".scr",
    ".pif",
    ".vbs",
    ".jse",
    ".wsf",
    ".wsh",
    ".ps1",
    ".psm1",
    ".sh",
    ".bash",
    ".jar",
    ".class",
    ".doc",
    ".xls",
}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024
DEFAULT_CHUNK_SIZE_BYTES = 5 * 1024 * 1024
MIN_CHUNK_SIZE_BYTES = 256 * 1024
MAX_CHUNK_SIZE_BYTES = 8 * 1024 * 1024
SESSION_TTL = timedelta(hours=24)
MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_FILES = 1000
MAX_ARCHIVE_DEPTH = 3


def _emit_event(
    outbox_port: OutboxPort | None,
    *,
    identity: IdentityContext,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: Mapping[str, Any],
    request_id: str,
    project_id: UUID | None = None,
    decision_unit_id: UUID | None = None,
) -> None:
    if outbox_port is None:
        return
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        occurred_at=datetime.now(timezone.utc),
        actor_id=identity.subject_id,
        request_id=request_id,
        correlation_id=uuid4(),
        causation_id=None,
        payload=dict(payload),
    )
    outbox_port.append(scope=identity.scope, event=envelope)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _filename_extension(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name
    if name != filename or name in {"", ".", ".."} or "/" in filename or "\\" in filename:
        raise BiaiceError(
            "REQUEST_VALIDATION_FAILED",
            detail="filename must be a basename without path separators.",
        )
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in BLOCKED_EXTENSIONS:
        raise BiaiceError(
            "DOCUMENT_TYPE_BLOCKED",
            detail=f"File extension {suffix} is not allowed.",
        )
    if suffix not in ALLOWED_EXTENSIONS:
        raise BiaiceError(
            "DOCUMENT_TYPE_BLOCKED",
            detail=f"File extension {suffix} is not in the allowed intake set.",
        )
    return suffix


def _sniff_content(data: bytes) -> tuple[str, DocumentMimeCategory]:
    if data.startswith(b"%PDF"):
        return "application/pdf", DocumentMimeCategory.PDF
    if data.startswith(b"\x89PNG"):
        return "image/png", DocumentMimeCategory.IMAGE
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", DocumentMimeCategory.IMAGE
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp", DocumentMimeCategory.IMAGE
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff", DocumentMimeCategory.IMAGE
    if data.startswith(b"PK\x03\x04"):
        return _sniff_zip(data)
    return "application/octet-stream", DocumentMimeCategory.UNKNOWN


def _archive_depth(name: str) -> int:
    return name.count("/") + name.count("\\")


def _sniff_zip(data: bytes) -> tuple[str, DocumentMimeCategory]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
    except zipfile.BadZipFile as exc:
        raise BiaiceError(
            "DOCUMENT_TYPE_BLOCKED",
            detail="Archive content could not be read safely.",
        ) from exc
    if len(infos) > MAX_ARCHIVE_FILES:
        raise BiaiceError(
            "DOCUMENT_TYPE_BLOCKED",
            detail="Archive contains too many files.",
        )
    total_size = 0
    names: list[str] = []
    for info in infos:
        if info.filename.startswith("/") or ".." in PurePosixPath(info.filename).parts:
            raise BiaiceError(
                "DOCUMENT_TYPE_BLOCKED",
                detail="Archive contains a path-traversal entry.",
            )
        if _archive_depth(info.filename) > MAX_ARCHIVE_DEPTH:
            raise BiaiceError(
                "DOCUMENT_TYPE_BLOCKED",
                detail="Archive nesting depth exceeds the intake limit.",
            )
        total_size += max(info.file_size, 0)
        if total_size > MAX_ARCHIVE_SIZE_BYTES:
            raise BiaiceError(
                "DOCUMENT_TYPE_BLOCKED",
                detail="Archive uncompressed size exceeds the intake limit.",
            )
        suffix = PurePosixPath(info.filename).suffix.lower()
        if suffix in BLOCKED_EXTENSIONS:
            raise BiaiceError(
                "DOCUMENT_TYPE_BLOCKED",
                detail="Archive contains a blocked executable or macro-capable type.",
            )
        names.append(info.filename.replace("\\", "/"))
    if any(name.startswith("word/") for name in names):
        return (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DocumentMimeCategory.DOCX,
        )
    if any(name.startswith("xl/") for name in names):
        return (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            DocumentMimeCategory.XLSX,
        )
    return "application/zip", DocumentMimeCategory.ARCHIVE


def _scan(data: bytes) -> tuple[ScanResult, str | None, str | None]:
    result = scan_bytes(data)
    return result.result, result.signature_version, result.details


def _document_target(document: SourceDocument) -> ScopedObjectRef:
    return ScopedObjectRef(
        tenant_id=document.tenant_id,
        data_domain_id=document.data_domain_id,
        project_id=document.project_id,
        decision_unit_id=document.decision_unit_id,
        object_type="SourceDocument",
        object_id=document.document_id,
        version_id=document.document_id,
    )


def _asset_target(asset: DerivedAsset) -> ScopedObjectRef:
    return ScopedObjectRef(
        tenant_id=asset.tenant_id,
        data_domain_id=asset.data_domain_id,
        object_type="DerivedAsset",
        object_id=asset.asset_id,
        version_id=asset.asset_id,
    )


class DocumentIntakeService:
    """Single writer for upload sessions and source-document lifecycle."""

    def __init__(
        self,
        *,
        repository: InMemoryDocumentsRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create_session(
        self,
        *,
        identity: IdentityContext,
        project_id: UUID | None,
        decision_unit_id: UUID | None,
        filename: str,
        file_size_bytes: int,
        declared_sha256: str,
        content_type: str,
        kind: DocumentKind,
        chunk_size_bytes: int,
        request_id: str,
    ) -> UploadSession:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        _filename_extension(filename)
        if file_size_bytes > MAX_FILE_SIZE_BYTES:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="file_size_bytes exceeds the 100MB intake limit.",
            )
        if not MIN_CHUNK_SIZE_BYTES <= chunk_size_bytes <= MAX_CHUNK_SIZE_BYTES:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="chunk_size_bytes is outside the allowed range.",
            )
        total_parts = (file_size_bytes + chunk_size_bytes - 1) // chunk_size_bytes
        now = self.clock.now()
        session = UploadSession(
            session_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
            kind=kind,
            filename=filename,
            file_size_bytes=file_size_bytes,
            content_type=content_type,
            mime_category=DocumentMimeCategory.UNKNOWN,
            declared_sha256=declared_sha256.lower(),
            chunk_size_bytes=chunk_size_bytes,
            total_parts=total_parts,
            received_parts=(),
            status=UploadSessionStatus.ACTIVE,
            created_by=identity.subject_id,
            created_at=now,
            expires_at=now + SESSION_TTL,
        )
        self.repository.upsert_session(session)
        self.audit_writer.write(
            identity=identity,
            action="documents.upload_session.create",
            object_type="UploadSession",
            object_id=session.session_id,
            request_id=request_id,
            reason_code="UPLOAD_SESSION_CREATED",
            outcome=session.status.value,
        )
        return session

    def get_session(self, *, identity: IdentityContext, session_id: UUID) -> UploadSession:
        session = self.repository.get_session(scope=identity.scope, session_id=session_id)
        if session is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"Upload session {session_id} not found in scope.",
            )
        return effective_upload_session(session, now=self.clock.now())

    def put_chunk(
        self,
        *,
        identity: IdentityContext,
        session_id: UUID,
        part_number: int,
        data: bytes,
        declared_chunk_sha256: str | None,
        request_id: str,
    ) -> UploadSession:
        require_audit(self.audit_writer)
        session = self.get_session(identity=identity, session_id=session_id)
        if session.status is UploadSessionStatus.EXPIRED:
            raise BiaiceError("UPLOAD_SESSION_EXPIRED")
        if session.status is not UploadSessionStatus.ACTIVE:
            raise BiaiceError("UPLOAD_SESSION_NOT_ACTIVE")
        if part_number > session.total_parts:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="part_number is outside the session part range.",
            )
        if not data:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="chunk body must not be empty.",
            )
        expected_size = session.chunk_size_bytes
        if part_number == session.total_parts:
            expected_size = session.file_size_bytes - session.chunk_size_bytes * (
                session.total_parts - 1
            )
        if len(data) != expected_size:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="chunk length does not match the session part size.",
            )
        digest = _sha256(data)
        if declared_chunk_sha256 and declared_chunk_sha256.lower() != digest:
            raise BiaiceError("UPLOAD_CHUNK_HASH_MISMATCH")
        now = self.clock.now()
        chunk = UploadChunkInfo(
            part_number=part_number,
            offset=(part_number - 1) * session.chunk_size_bytes,
            size_bytes=len(data),
            expected_sha256=digest,
            received_sha256=digest,
            received_at=now,
        )
        self.repository.put_chunk(session_id=session.session_id, part_number=part_number, data=data)
        remaining = [item for item in session.received_parts if item.part_number != part_number]
        updated = session.model_copy(
            update={
                "received_parts": tuple(
                    sorted((*remaining, chunk), key=lambda item: item.part_number)
                )
            }
        )
        self.repository.upsert_session(updated)
        self.audit_writer.write(
            identity=identity,
            action="documents.upload_session.chunk",
            object_type="UploadSession",
            object_id=session.session_id,
            request_id=request_id,
            reason_code="UPLOAD_CHUNK_RECEIVED",
            outcome=updated.status.value,
        )
        return updated

    def complete(
        self, *, identity: IdentityContext, session_id: UUID, request_id: str
    ) -> tuple[UploadSession, SourceDocument]:
        require_audit(self.audit_writer)
        session = self.get_session(identity=identity, session_id=session_id)
        if session.status is UploadSessionStatus.COMPLETED and session.document_id:
            document = self.get_document(identity=identity, document_id=session.document_id)
            return session, document
        if session.status is UploadSessionStatus.EXPIRED:
            raise BiaiceError("UPLOAD_SESSION_EXPIRED")
        if session.status is not UploadSessionStatus.ACTIVE:
            raise BiaiceError("UPLOAD_SESSION_NOT_ACTIVE")
        missing = missing_part_numbers(session)
        if missing:
            raise BiaiceError(
                "UPLOAD_INCOMPLETE",
                detail=f"Missing parts: {', '.join(str(part) for part in missing)}.",
            )
        payload = self.repository.compose_chunks(
            session_id=session.session_id, total_parts=session.total_parts
        )
        digest = _sha256(payload)
        if len(payload) != session.file_size_bytes or digest != session.declared_sha256:
            raise BiaiceError("UPLOAD_HASH_MISMATCH")
        sniffed_type, mime_category = _sniff_content(payload)
        scan_result, signature, details = _scan(payload)
        if scan_result is not ScanResult.INFECTED and mime_category in {
            DocumentMimeCategory.UNKNOWN,
            DocumentMimeCategory.BLOCKED,
        }:
            raise BiaiceError(
                "DOCUMENT_TYPE_BLOCKED",
                detail="Sniffed MIME type is not allowed for intake.",
            )
        existing = self.repository.find_by_content_hash(scope=identity.scope, content_hash=digest)
        now = self.clock.now()
        if existing is not None:
            completed = session.model_copy(
                update={
                    "status": UploadSessionStatus.COMPLETED,
                    "final_sha256": digest,
                    "final_size_bytes": len(payload),
                    "quarantine_key": existing.storage_key,
                    "document_id": existing.document_id,
                    "mime_category": existing.mime_category,
                    "completed_at": now,
                }
            )
            self.repository.upsert_session(completed)
            self.repository.drop_chunks(session_id=session.session_id)
            return completed, existing
        document_id = uuid4()
        storage_key = f"quarantine/{session.tenant_id}/{session.session_id}/{session.filename}"
        locator_hash = self.repository.put_blob(storage_key, payload)
        status = (
            DocumentStatus.SCAN_FAILED
            if scan_result is ScanResult.INFECTED
            else DocumentStatus.SCAN_PASSED
        )
        document = SourceDocument(
            document_id=document_id,
            tenant_id=session.tenant_id,
            data_domain_id=session.data_domain_id,
            project_id=session.project_id,
            decision_unit_id=session.decision_unit_id,
            kind=session.kind,
            name=session.filename,
            storage_key=storage_key,
            storage_locator_hash=locator_hash,
            size_bytes=len(payload),
            content_hash=digest,
            declared_content_type=session.content_type,
            sniffed_content_type=sniffed_type,
            mime_category=mime_category,
            scan_result=scan_result,
            scan_signature_version=signature,
            scan_details=details,
            status=status,
            quarantined_at=now,
            scan_completed_at=now,
            uploaded_by=session.created_by,
            uploaded_at=now,
            upload_session_id=session.session_id,
            source_filename=session.filename,
        )
        completed = session.model_copy(
            update={
                "status": UploadSessionStatus.COMPLETED,
                "final_sha256": digest,
                "final_size_bytes": len(payload),
                "quarantine_key": storage_key,
                "document_id": document_id,
                "mime_category": mime_category,
                "completed_at": now,
            }
        )
        self.repository.upsert_document(document)
        self.repository.upsert_session(completed)
        self.repository.drop_chunks(session_id=session.session_id)
        self._register_replica(target=_document_target(document), locator_hash=locator_hash)
        self.audit_writer.write(
            identity=identity,
            action="documents.source_document.upload",
            object_type="SourceDocument",
            object_id=document.document_id,
            request_id=request_id,
            reason_code="SOURCE_DOCUMENT_UPLOADED",
            outcome=document.status.value,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="documents.source_document_uploaded.v1",
            aggregate_type="SourceDocument",
            aggregate_id=document.document_id,
            payload={
                "document_id": str(document.document_id),
                "session_id": str(session.session_id),
                "status": document.status.value,
                "scan_result": document.scan_result.value,
                "content_hash": document.content_hash,
            },
            request_id=request_id,
            project_id=document.project_id,
            decision_unit_id=document.decision_unit_id,
        )
        if document.status is DocumentStatus.SCAN_FAILED:
            _emit_event(
                self.outbox_port,
                identity=identity,
                event_type="documents.document_quarantined.v1",
                aggregate_type="SourceDocument",
                aggregate_id=document.document_id,
                payload={
                    "document_id": str(document.document_id),
                    "status": document.status.value,
                    "scan_result": document.scan_result.value,
                },
                request_id=request_id,
                project_id=document.project_id,
                decision_unit_id=document.decision_unit_id,
            )
        return completed, document

    def cancel(
        self, *, identity: IdentityContext, session_id: UUID, request_id: str
    ) -> UploadSession:
        require_audit(self.audit_writer)
        session = self.get_session(identity=identity, session_id=session_id)
        if session.status is UploadSessionStatus.CANCELLED:
            return session
        if session.status is UploadSessionStatus.COMPLETED:
            raise BiaiceError("UPLOAD_SESSION_NOT_ACTIVE")
        cancelled = session.model_copy(
            update={
                "status": UploadSessionStatus.CANCELLED,
                "completed_at": self.clock.now(),
            }
        )
        self.repository.upsert_session(cancelled)
        self.repository.drop_chunks(session_id=session.session_id)
        self.audit_writer.write(
            identity=identity,
            action="documents.upload_session.cancel",
            object_type="UploadSession",
            object_id=session.session_id,
            request_id=request_id,
            reason_code="UPLOAD_SESSION_CANCELLED",
            outcome=cancelled.status.value,
        )
        return cancelled

    def list_documents(
        self,
        *,
        identity: IdentityContext,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
    ) -> tuple[SourceDocument, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        native = self.repository.list_documents(
            scope=identity.scope,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        if decision_unit_id is None:
            return native
        linked: list[SourceDocument] = []
        seen = {item.document_id for item in native}
        for link in self.repository.list_active_links(
            scope=identity.scope, decision_unit_id=decision_unit_id
        ):
            if link.source_document_id in seen:
                continue
            document = self.repository.get_document(
                scope=identity.scope, document_id=link.source_document_id
            )
            if document is None:
                continue
            linked.append(document)
            seen.add(document.document_id)
        merged = [*native, *linked]
        merged.sort(key=lambda item: (item.uploaded_at, str(item.document_id)))
        return tuple(merged)

    def get_document(self, *, identity: IdentityContext, document_id: UUID) -> SourceDocument:
        document = self.repository.get_document(scope=identity.scope, document_id=document_id)
        if document is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"Document {document_id} not found in scope.",
            )
        return document

    def review(
        self, *, identity: IdentityContext, document_id: UUID, request_id: str
    ) -> SourceDocument:
        require_audit(self.audit_writer)
        document = self.get_document(identity=identity, document_id=document_id)
        if document.status is DocumentStatus.SCAN_FAILED:
            raise BiaiceError("DOCUMENT_SCAN_FAILED")
        if document.status is not DocumentStatus.SCAN_PASSED:
            raise BiaiceError("DOCUMENT_NOT_REVIEWABLE")
        now = self.clock.now()
        reviewed = document.model_copy(
            update={
                "status": DocumentStatus.UNDER_REVIEW,
                "reviewed_by": identity.subject_id,
                "reviewed_at": now,
            }
        )
        self.repository.upsert_document(reviewed)
        self.audit_writer.write(
            identity=identity,
            action="documents.source_document.review",
            object_type="SourceDocument",
            object_id=reviewed.document_id,
            request_id=request_id,
            reason_code="DOCUMENT_REVIEW_STARTED",
            outcome=reviewed.status.value,
        )
        return reviewed

    def release(
        self, *, identity: IdentityContext, document_id: UUID, request_id: str
    ) -> SourceDocument:
        require_audit(self.audit_writer)
        document = self.get_document(identity=identity, document_id=document_id)
        if document.status is DocumentStatus.RELEASED:
            raise BiaiceError("DOCUMENT_ALREADY_RELEASED")
        if document.status is DocumentStatus.SCAN_FAILED:
            raise BiaiceError("DOCUMENT_SCAN_FAILED")
        if document.status is not DocumentStatus.UNDER_REVIEW:
            raise BiaiceError("DOCUMENT_NOT_RELEASABLE")
        if identity.subject_id == document.uploaded_by:
            raise BiaiceError(
                "MAKER_CHECKER_REQUIRED",
                detail="The uploader cannot release the document from quarantine.",
            )
        now = self.clock.now()
        released = document.model_copy(
            update={
                "status": DocumentStatus.RELEASED,
                "released_by": identity.subject_id,
                "released_at": now,
            }
        )
        self.repository.upsert_document(released)
        self.audit_writer.write(
            identity=identity,
            action="documents.source_document.release",
            object_type="SourceDocument",
            object_id=released.document_id,
            request_id=request_id,
            reason_code="SOURCE_DOCUMENT_RELEASED",
            outcome=released.status.value,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="documents.source_document_released.v1",
            aggregate_type="SourceDocument",
            aggregate_id=released.document_id,
            payload={
                "document_id": str(released.document_id),
                "status": released.status.value,
                "released_by": str(released.released_by),
            },
            request_id=request_id,
            project_id=released.project_id,
            decision_unit_id=released.decision_unit_id,
        )
        return released

    def quarantine(
        self, *, identity: IdentityContext, document_id: UUID, request_id: str
    ) -> SourceDocument:
        require_audit(self.audit_writer)
        document = self.get_document(identity=identity, document_id=document_id)
        if document.status is DocumentStatus.QUARANTINED:
            return document
        if document.status not in {
            DocumentStatus.SCAN_PASSED,
            DocumentStatus.UNDER_REVIEW,
            DocumentStatus.RELEASED,
        }:
            raise BiaiceError("DOCUMENT_NOT_RELEASABLE")
        now = self.clock.now()
        quarantined = document.model_copy(
            update={
                "status": DocumentStatus.QUARANTINED,
                "quarantined_at": now,
                "released_at": None,
                "released_by": None,
            }
        )
        self.repository.upsert_document(quarantined)
        self.audit_writer.write(
            identity=identity,
            action="documents.source_document.quarantine",
            object_type="SourceDocument",
            object_id=quarantined.document_id,
            request_id=request_id,
            reason_code="DOCUMENT_QUARANTINED",
            outcome=quarantined.status.value,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="documents.document_quarantined.v1",
            aggregate_type="SourceDocument",
            aggregate_id=quarantined.document_id,
            payload={
                "document_id": str(quarantined.document_id),
                "status": quarantined.status.value,
                "scan_result": quarantined.scan_result.value,
            },
            request_id=request_id,
            project_id=quarantined.project_id,
            decision_unit_id=quarantined.decision_unit_id,
        )
        return quarantined

    def download(
        self, *, identity: IdentityContext, document_id: UUID
    ) -> tuple[SourceDocument, bytes]:
        document = self.get_document(identity=identity, document_id=document_id)
        if document.status not in downloadable_statuses():
            raise BiaiceError("DOCUMENT_NOT_DOWNLOADABLE")
        payload = self.repository.get_blob(document.storage_key)
        if payload is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail="Document bytes are not available in object storage.",
            )
        return document, payload

    def create_parse_job(
        self,
        *,
        identity: IdentityContext,
        document_id: UUID,
        project_id: UUID | None,
        decision_unit_id: UUID | None,
        request_id: str,
        execute: bool = True,
    ) -> ParseJob:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        document = self.get_document(identity=identity, document_id=document_id)
        if project_id is not None and document.project_id not in {project_id, None}:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"Document {document_id} not found in project scope.",
            )
        if (
            decision_unit_id is not None
            and document.decision_unit_id not in {decision_unit_id, None}
            and not self._document_linked_to_unit(
                identity=identity,
                document_id=document_id,
                decision_unit_id=decision_unit_id,
            )
        ):
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"Document {document_id} not found in unit scope.",
            )
        if document.status not in parsable_statuses():
            raise BiaiceError("DOCUMENT_NOT_PARSABLE")
        now = self.clock.now()
        job = ParseJob(
            job_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id or document.project_id,
            decision_unit_id=decision_unit_id or document.decision_unit_id,
            document_id=document.document_id,
            document_version_id=document.document_id,
            status=ParseStatus.QUEUED,
            stage="QUEUED",
            progress_percent=0,
            created_at=now,
            created_by=identity.subject_id,
        )
        self.repository.upsert_parse_job(job)
        self.audit_writer.write(
            identity=identity,
            action="documents.parse_job.create",
            object_type="ParseJob",
            object_id=job.job_id,
            request_id=request_id,
            reason_code="PARSE_JOB_CREATED",
            outcome=job.status.value,
        )
        if execute:
            return self.execute_parse_job(
                identity=identity, job_id=job.job_id, request_id=request_id
            )
        return job

    def get_parse_job(self, *, identity: IdentityContext, job_id: UUID) -> ParseJob:
        job = self.repository.get_parse_job(scope=identity.scope, job_id=job_id)
        if job is None:
            raise BiaiceError("JOB_NOT_FOUND", detail=f"Parse job {job_id} not found in scope.")
        return job

    def execute_parse_job_for_worker(self, *, job_id: UUID, request_id: str) -> ParseJob:
        job = self.repository.get_parse_job_unscoped(job_id)
        if job is None:
            raise BiaiceError("JOB_NOT_FOUND", detail=f"Parse job {job_id} not found.")
        identity = IdentityContext(
            subject_id=job.created_by,
            username="ingest-worker",
            display_name="Ingest worker",
            roles=frozenset({Role.DOCUMENT_SPECIALIST}),
            scope=TenantScope(
                tenant_id=job.tenant_id,
                data_domain_id=job.data_domain_id,
                all_projects=True,
                all_decision_units=True,
            ),
            mfa_verified=True,
            authenticated_at=self.clock.now(),
        )
        return self.execute_parse_job(identity=identity, job_id=job_id, request_id=request_id)

    def execute_parse_job(
        self, *, identity: IdentityContext, job_id: UUID, request_id: str
    ) -> ParseJob:
        require_audit(self.audit_writer)
        job = self.get_parse_job(identity=identity, job_id=job_id)
        if job.status not in {ParseStatus.QUEUED, ParseStatus.FAILED}:
            return job
        document = self.get_document(identity=identity, document_id=job.document_id)
        now = self.clock.now()
        running = job.model_copy(
            update={
                "status": ParseStatus.RUNNING,
                "stage": "EXTRACT",
                "progress_percent": 40,
                "started_at": now,
                "failure_reason_code": None,
                "failure_detail": None,
                "retryable": None,
            }
        )
        self.repository.upsert_parse_job(running)
        payload = self.repository.get_blob(document.storage_key)
        if payload is None:
            failed = running.model_copy(
                update={
                    "status": ParseStatus.FAILED,
                    "stage": "FAILED",
                    "progress_percent": 100,
                    "completed_at": self.clock.now(),
                    "retryable": ParseRetryable.YES,
                    "failure_reason_code": "BLOB_MISSING",
                    "failure_detail": "Source bytes were not found in object storage.",
                }
            )
            self.repository.upsert_parse_job(failed)
            self._emit_parse_failed(identity, failed, request_id)
            return failed
        extracting = running.model_copy(update={"stage": "PERSIST", "progress_percent": 70})
        self.repository.upsert_parse_job(extracting)
        outcome = parse_document(payload, document.mime_category)
        finished_at = self.clock.now()
        if outcome.status is ParseStatus.FAILED:
            failed = extracting.model_copy(
                update={
                    "status": ParseStatus.FAILED,
                    "stage": "FAILED",
                    "progress_percent": 100,
                    "completed_at": finished_at,
                    "retryable": outcome.retryable,
                    "failure_reason_code": outcome.failure_reason_code,
                    "failure_detail": outcome.failure_detail,
                }
            )
            self.repository.upsert_parse_job(failed)
            self._emit_parse_failed(identity, failed, request_id)
            return failed
        asset_id = uuid4()
        storage_key = f"derived/{document.tenant_id}/{document.document_id}/{asset_id}.txt"
        encoded = outcome.text.encode("utf-8")
        locator_hash = self.repository.put_blob(storage_key, encoded)
        fragment_ref = f"doc:{document.document_id}/fragment:{asset_id}"
        asset = DerivedAsset(
            asset_id=asset_id,
            tenant_id=document.tenant_id,
            data_domain_id=document.data_domain_id,
            source_document_id=document.document_id,
            source_document_version_id=document.document_id,
            parse_job_id=job.job_id,
            kind=(
                DerivedAssetKind.OCR_TEXT
                if document.mime_category is DocumentMimeCategory.PDF
                else DerivedAssetKind.EXTRACTED_CONTENT
            ),
            name="extracted-text",
            description="Stdlib extracted text or archive listing",
            storage_key=storage_key,
            storage_locator_hash=locator_hash,
            size_bytes=len(encoded),
            content_hash=_sha256(encoded),
            mime_type="text/plain",
            page_number=1 if outcome.page_count else None,
            fragment_ref=fragment_ref,
            created_at=finished_at,
        )
        self.repository.upsert_derived_asset(asset)
        self._register_replica(target=_asset_target(asset), locator_hash=locator_hash)
        succeeded = extracting.model_copy(
            update={
                "status": ParseStatus.SUCCEEDED,
                "stage": "SUCCEEDED",
                "progress_percent": 100,
                "completed_at": finished_at,
                "derived_asset_ids": (asset.asset_id,),
            }
        )
        self.repository.upsert_parse_job(succeeded)
        self.audit_writer.write(
            identity=identity,
            action="documents.parse_job.complete",
            object_type="ParseJob",
            object_id=succeeded.job_id,
            request_id=request_id,
            reason_code="PARSE_COMPLETED",
            outcome=succeeded.status.value,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="documents.parse_completed.v1",
            aggregate_type="ParseJob",
            aggregate_id=succeeded.job_id,
            payload={
                "parse_job_id": str(succeeded.job_id),
                "document_id": str(document.document_id),
                "status": succeeded.status.value,
            },
            request_id=request_id,
            project_id=document.project_id,
            decision_unit_id=document.decision_unit_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="documents.derived_asset_registered.v1",
            aggregate_type="DerivedAsset",
            aggregate_id=asset.asset_id,
            payload={
                "derived_asset_id": str(asset.asset_id),
                "document_id": str(document.document_id),
                "fragment_ref": asset.fragment_ref,
            },
            request_id=request_id,
            project_id=document.project_id,
            decision_unit_id=document.decision_unit_id,
        )
        return succeeded

    def retry_parse_job(
        self, *, identity: IdentityContext, job_id: UUID, request_id: str
    ) -> ParseJob:
        job = self.get_parse_job(identity=identity, job_id=job_id)
        if job.status is not ParseStatus.FAILED or job.retryable is not ParseRetryable.YES:
            raise BiaiceError("JOB_NOT_RETRYABLE")
        if job.attempt >= job.max_attempts:
            raise BiaiceError("JOB_NOT_RETRYABLE")
        queued = job.model_copy(
            update={
                "status": ParseStatus.QUEUED,
                "stage": "QUEUED",
                "progress_percent": 0,
                "attempt": job.attempt + 1,
                "completed_at": None,
                "started_at": None,
            }
        )
        self.repository.upsert_parse_job(queued)
        return self.execute_parse_job(
            identity=identity, job_id=queued.job_id, request_id=request_id
        )

    def cancel_parse_job(
        self, *, identity: IdentityContext, job_id: UUID, request_id: str
    ) -> ParseJob:
        require_audit(self.audit_writer)
        job = self.get_parse_job(identity=identity, job_id=job_id)
        if job.status is ParseStatus.CANCELLED:
            return job
        if job.status is not ParseStatus.QUEUED:
            raise BiaiceError("JOB_NOT_CANCELLABLE")
        cancelled = job.model_copy(
            update={
                "status": ParseStatus.CANCELLED,
                "stage": "CANCELLED",
                "cancelled_at": self.clock.now(),
                "completed_at": self.clock.now(),
            }
        )
        self.repository.upsert_parse_job(cancelled)
        self.audit_writer.write(
            identity=identity,
            action="documents.parse_job.cancel",
            object_type="ParseJob",
            object_id=cancelled.job_id,
            request_id=request_id,
            reason_code="PARSE_JOB_CANCELLED",
            outcome=cancelled.status.value,
        )
        return cancelled

    def list_derived_assets(
        self, *, identity: IdentityContext, document_id: UUID
    ) -> tuple[DerivedAsset, ...]:
        self.get_document(identity=identity, document_id=document_id)
        return self.repository.list_derived_assets(scope=identity.scope, document_id=document_id)

    def get_derived_asset(self, *, identity: IdentityContext, asset_id: UUID) -> DerivedAsset:
        asset = self.repository.get_derived_asset(scope=identity.scope, asset_id=asset_id)
        if asset is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"Derived asset {asset_id} not found in scope.",
            )
        return asset

    def list_replicas(self, *, identity: IdentityContext) -> tuple[ReplicaLocation, ...]:
        return self.repository.list_replicas(scope=identity.scope)

    def inherit_to_unit(
        self,
        *,
        identity: IdentityContext,
        document_id: UUID,
        decision_unit_id: UUID,
        reason: str | None,
        request_id: str,
    ) -> DocumentLink:
        return self._create_link(
            identity=identity,
            document_id=document_id,
            decision_unit_id=decision_unit_id,
            relation=DocumentLinkRelation.INHERITED,
            priority=0,
            reason=reason,
            request_id=request_id,
            action="documents.document_link.inherit",
        )

    def override_link(
        self,
        *,
        identity: IdentityContext,
        document_id: UUID,
        decision_unit_id: UUID,
        reason: str,
        priority: int,
        request_id: str,
    ) -> DocumentLink:
        if not reason.strip():
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="override requires a human-readable reason.",
            )
        return self._create_link(
            identity=identity,
            document_id=document_id,
            decision_unit_id=decision_unit_id,
            relation=DocumentLinkRelation.OVERRIDE,
            priority=priority,
            reason=reason,
            request_id=request_id,
            action="documents.document_link.override",
        )

    def resolve_conflict(
        self,
        *,
        identity: IdentityContext,
        link_id: UUID,
        chosen_document_id: UUID,
        reason: str,
        request_id: str,
    ) -> DocumentLink:
        require_audit(self.audit_writer)
        if not reason.strip():
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="conflict resolution requires a confirmation reason.",
            )
        chosen_link = self._get_link(identity=identity, link_id=link_id)
        if chosen_link.detached_at is not None:
            raise BiaiceError("DOCUMENT_LINK_NOT_RESOLVABLE")
        if chosen_link.source_document_id != chosen_document_id:
            raise BiaiceError(
                "DOCUMENT_LINK_NOT_RESOLVABLE",
                detail="chosen_document_id must match the submitted link.",
            )
        if chosen_link.conflict_state is not DocumentLinkConflictState.OPEN:
            raise BiaiceError("DOCUMENT_LINK_NOT_RESOLVABLE")
        now = self.clock.now()
        resolved = chosen_link.model_copy(
            update={
                "conflict_state": DocumentLinkConflictState.RESOLVED,
                "confirmation_reason": reason,
                "confirmed_by": identity.subject_id,
            }
        )
        self.repository.upsert_link(resolved)
        for other in self.repository.list_active_links(
            scope=identity.scope, decision_unit_id=chosen_link.decision_unit_id
        ):
            if other.link_id == resolved.link_id:
                continue
            other_document = self.repository.get_document(
                scope=identity.scope, document_id=other.source_document_id
            )
            chosen_document = self.repository.get_document(
                scope=identity.scope, document_id=chosen_document_id
            )
            if (
                other_document is None
                or chosen_document is None
                or other_document.kind != chosen_document.kind
            ):
                continue
            self.repository.upsert_link(
                other.model_copy(
                    update={
                        "detached_at": now,
                        "conflict_state": DocumentLinkConflictState.RESOLVED,
                        "confirmation_reason": reason,
                        "confirmed_by": identity.subject_id,
                    }
                )
            )
        self.audit_writer.write(
            identity=identity,
            action="documents.document_link.resolve",
            object_type="DocumentLink",
            object_id=resolved.link_id,
            request_id=request_id,
            reason_code="DOCUMENT_LINK_RESOLVED",
            outcome=resolved.conflict_state.value,
        )
        return resolved

    def detach_link(
        self, *, identity: IdentityContext, link_id: UUID, request_id: str
    ) -> DocumentLink:
        require_audit(self.audit_writer)
        link = self._get_link(identity=identity, link_id=link_id)
        if link.detached_at is not None:
            return link
        detached = link.model_copy(update={"detached_at": self.clock.now()})
        self.repository.upsert_link(detached)
        self.audit_writer.write(
            identity=identity,
            action="documents.document_link.detach",
            object_type="DocumentLink",
            object_id=detached.link_id,
            request_id=request_id,
            reason_code="DOCUMENT_LINK_DETACHED",
            outcome="DETACHED",
        )
        return detached

    def _get_link(self, *, identity: IdentityContext, link_id: UUID) -> DocumentLink:
        link = self.repository.get_link(scope=identity.scope, link_id=link_id)
        if link is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"Document link {link_id} not found in scope.",
            )
        return link

    def _document_linked_to_unit(
        self,
        *,
        identity: IdentityContext,
        document_id: UUID,
        decision_unit_id: UUID,
    ) -> bool:
        return any(
            link.source_document_id == document_id
            for link in self.repository.list_active_links(
                scope=identity.scope, decision_unit_id=decision_unit_id
            )
        )

    def _create_link(
        self,
        *,
        identity: IdentityContext,
        document_id: UUID,
        decision_unit_id: UUID,
        relation: DocumentLinkRelation,
        priority: int,
        reason: str | None,
        request_id: str,
        action: str,
    ) -> DocumentLink:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        document = self.get_document(identity=identity, document_id=document_id)
        existing = [
            link
            for link in self.repository.list_active_links(
                scope=identity.scope, decision_unit_id=decision_unit_id
            )
            if link.source_document_id == document_id
        ]
        if existing:
            return existing[0]
        same_kind = []
        for link in self.repository.list_active_links(
            scope=identity.scope, decision_unit_id=decision_unit_id
        ):
            other = self.repository.get_document(
                scope=identity.scope, document_id=link.source_document_id
            )
            if other is not None and other.kind is document.kind:
                same_kind.append(link)
        conflict = DocumentLinkConflictState.OPEN if same_kind else DocumentLinkConflictState.NONE
        now = self.clock.now()
        created = DocumentLink(
            link_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            source_document_id=document.document_id,
            project_id=document.project_id,
            decision_unit_id=decision_unit_id,
            relation=relation,
            priority=priority,
            conflict_state=conflict,
            confirmation_reason=reason,
            created_by=identity.subject_id,
            created_at=now,
        )
        self.repository.upsert_link(created)
        if conflict is DocumentLinkConflictState.OPEN:
            for link in same_kind:
                self.repository.upsert_link(
                    link.model_copy(update={"conflict_state": DocumentLinkConflictState.OPEN})
                )
        self.audit_writer.write(
            identity=identity,
            action=action,
            object_type="DocumentLink",
            object_id=created.link_id,
            request_id=request_id,
            reason_code=relation.value,
            outcome=created.conflict_state.value,
        )
        return created

    def _register_replica(self, *, target: ScopedObjectRef, locator_hash: str) -> ReplicaLocation:
        replica = ReplicaLocation(
            replica_id=uuid4(),
            target=target,
            kind=ReplicaKind.OBJECT_STORAGE,
            adapter_name=MEMBER3_ADAPTER_NAME,
            adapter_owner=AdapterOwner.MEMBER_3_LOCAL_REPLICA,
            locator_hash=locator_hash,
            required_for_completion=True,
            deletion_sla_seconds=DELETION_SLA_SECONDS,
        )
        self.repository.upsert_replica(replica)
        return replica

    def _emit_parse_failed(self, identity: IdentityContext, job: ParseJob, request_id: str) -> None:
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="documents.parse_failed.v1",
            aggregate_type="ParseJob",
            aggregate_id=job.job_id,
            payload={
                "parse_job_id": str(job.job_id),
                "document_id": str(job.document_id),
                "status": job.status.value,
                "retryable": None if job.retryable is None else job.retryable.value,
            },
            request_id=request_id,
            project_id=job.project_id,
            decision_unit_id=job.decision_unit_id,
        )


class DocumentReadService:
    def __init__(self, repository: InMemoryDocumentsRepository) -> None:
        self.repository = repository

    def get_released_document(
        self, *, scope: TenantScope, document_id: UUID
    ) -> ReleasedDocumentView | None:
        document = self.repository.get_document(scope=scope, document_id=document_id)
        if document is None or document.status is not DocumentStatus.RELEASED:
            return None
        assets = self.repository.list_derived_assets(scope=scope, document_id=document_id)
        latest_job_status: ParseStatus | None = None
        return ReleasedDocumentView(
            document_id=document.document_id,
            content_hash=document.content_hash,
            status=document.status,
            parse_status=latest_job_status if not assets else ParseStatus.SUCCEEDED,
            fragment_refs=tuple(asset.fragment_ref for asset in assets),
            reviewed_by=document.reviewed_by,
            released_by=document.released_by,
            uploaded_at=document.uploaded_at,
        )

    def get_fragment(self, *, scope: TenantScope, asset_id: UUID) -> DerivedAsset | None:
        asset = self.repository.get_derived_asset(scope=scope, asset_id=asset_id)
        if asset is None:
            return None
        document = self.repository.get_document(scope=scope, document_id=asset.source_document_id)
        if document is None or document.status is not DocumentStatus.RELEASED:
            return None
        return asset


class DocumentsServices:
    def __init__(
        self,
        *,
        repository: InMemoryDocumentsRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        legal_holds: LegalHoldQueryPort | None = None,
    ) -> None:
        self.repository = repository
        self.legal_holds = legal_holds or NoLegalHolds()
        self.intake = DocumentIntakeService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.read_port: DocumentReadPort = DocumentReadService(repository)


def configure_documents(
    app,
    *,
    repository: InMemoryDocumentsRepository | None = None,
    legal_holds: LegalHoldQueryPort | None = None,
) -> DocumentsServices:
    from biaice.modules.documents.infrastructure.deletion_adapters.local_storage import (
        LocalReplicaDeletionAdapter,
    )
    from biaice.workers.ingest.runtime import bind_runtime

    repository = repository or InMemoryDocumentsRepository()
    clock = SystemClock()
    services = DocumentsServices(
        repository=repository,
        clock=clock,
        audit_writer=app.state.audit_writer,
        outbox_port=getattr(app.state, "outbox_port", None),
        legal_holds=legal_holds,
    )
    adapter = LocalReplicaDeletionAdapter(
        repository=repository,
        legal_holds=services.legal_holds,
        clock=clock,
    )
    app.state.documents_repository = repository
    app.state.documents_services = services
    app.state.document_read_port = services.read_port
    app.state.member3_replica_deletion_adapter = adapter
    bind_runtime(services.intake)
    return services
