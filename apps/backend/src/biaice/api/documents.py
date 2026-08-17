"""FR-02 member-3 document intake router (upload, scan, parse, links)."""

from __future__ import annotations

import io
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.documents.application.services import (
    DEFAULT_CHUNK_SIZE_BYTES,
    MAX_CHUNK_SIZE_BYTES,
    MAX_FILE_SIZE_BYTES,
    MIN_CHUNK_SIZE_BYTES,
    DocumentIntakeService,
    DocumentsServices,
)
from biaice.modules.documents.domain.models import (
    DerivedAsset,
    DocumentKind,
    DocumentLink,
    ParseJob,
    SourceDocument,
    UploadSession,
    missing_part_numbers,
    next_upload_action,
)
from biaice.modules.governance.domain.models import ReplicaLocation

router = APIRouter(prefix="/api/v1", tags=["documents"])


def get_documents_services(request: Request) -> DocumentsServices:
    services = getattr(request.app.state, "documents_services", None)
    if services is None:
        raise BiaiceError(
            "INTERNAL_ERROR",
            detail="Document intake services are not configured on app.state.",
        )
    return services


def get_intake_service(request: Request) -> DocumentIntakeService:
    return get_documents_services(request).intake


class CreateUploadSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=500)
    file_size_bytes: int = Field(ge=1, le=MAX_FILE_SIZE_BYTES)
    declared_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    content_type: str = Field(default="application/octet-stream", max_length=100)
    kind: DocumentKind = DocumentKind.TENDER
    chunk_size_bytes: int = Field(
        default=DEFAULT_CHUNK_SIZE_BYTES,
        ge=MIN_CHUNK_SIZE_BYTES,
        le=MAX_CHUNK_SIZE_BYTES,
    )


class UploadChunkResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    part_number: int
    offset: int
    size_bytes: int
    expected_sha256: str
    received_sha256: str | None
    received_at: str | None


class UploadSessionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: UUID
    status: str
    kind: DocumentKind
    filename: str
    file_size_bytes: int
    content_type: str
    mime_category: str
    declared_sha256: str
    chunk_size_bytes: int
    total_parts: int
    received_parts: tuple[UploadChunkResponse, ...]
    next_action: str
    missing_part_numbers: tuple[int, ...]
    document_id: UUID | None
    expires_at: str
    created_at: str
    completed_at: str | None


class CompleteUploadResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session: UploadSessionResponse
    document: SourceDocument


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[SourceDocument, ...]


class CreateParseJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID


class ParseJobResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    parse_job_id: UUID
    document_id: UUID
    status: str
    stage: str | None
    progress_percent: int
    retryable: str | None
    failure_reason_code: str | None
    failure_detail: str | None
    attempt: int
    max_attempts: int
    derived_asset_ids: tuple[UUID, ...]
    created_at: str
    started_at: str | None
    completed_at: str | None


class DerivedAssetListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[DerivedAsset, ...]


class ReplicaListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[ReplicaLocation, ...]


class InheritDocumentLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    decision_unit_id: UUID
    reason: str | None = Field(default=None, max_length=1000)


class OverrideDocumentLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    decision_unit_id: UUID
    reason: str = Field(min_length=1, max_length=1000)
    priority: int = Field(default=1, ge=1, le=100)


class ResolveConflictDocumentLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: UUID
    chosen_document_id: UUID
    reason: str = Field(min_length=1, max_length=1000)


class DetachDocumentLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: UUID


def _session_response(session: UploadSession) -> UploadSessionResponse:
    return UploadSessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        kind=session.kind,
        filename=session.filename,
        file_size_bytes=session.file_size_bytes,
        content_type=session.content_type,
        mime_category=session.mime_category.value,
        declared_sha256=session.declared_sha256,
        chunk_size_bytes=session.chunk_size_bytes,
        total_parts=session.total_parts,
        received_parts=tuple(
            UploadChunkResponse(
                part_number=part.part_number,
                offset=part.offset,
                size_bytes=part.size_bytes,
                expected_sha256=part.expected_sha256,
                received_sha256=part.received_sha256,
                received_at=part.received_at.isoformat() if part.received_at else None,
            )
            for part in session.received_parts
        ),
        next_action=next_upload_action(session).value,
        missing_part_numbers=missing_part_numbers(session),
        document_id=session.document_id,
        expires_at=session.expires_at.isoformat(),
        created_at=session.created_at.isoformat(),
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
    )


def _parse_job_response(job: ParseJob) -> ParseJobResponse:
    return ParseJobResponse(
        parse_job_id=job.job_id,
        document_id=job.document_id,
        status=job.status.value,
        stage=job.stage,
        progress_percent=job.progress_percent,
        retryable=None if job.retryable is None else job.retryable.value,
        failure_reason_code=job.failure_reason_code,
        failure_detail=job.failure_detail,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        derived_asset_ids=job.derived_asset_ids,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


@router.post(
    "/projects/{project_id}/document-upload-sessions",
    operation_id="create_project_document_upload_session",
    response_model=UploadSessionResponse,
    responses=PROBLEM_RESPONSES,
)
def create_project_document_upload_session(
    body: CreateUploadSessionRequest,
    request: Request,
    project_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.DOCUMENTS_CREATE)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> UploadSessionResponse:
    del idempotency_key
    session = service.create_session(
        identity=identity,
        project_id=project_id,
        decision_unit_id=None,
        filename=body.filename,
        file_size_bytes=body.file_size_bytes,
        declared_sha256=body.declared_sha256,
        content_type=body.content_type,
        kind=body.kind,
        chunk_size_bytes=body.chunk_size_bytes,
        request_id=request.state.request_id,
    )
    return _session_response(session)


@router.post(
    "/decision-units/{unit_id}/document-upload-sessions",
    operation_id="create_unit_document_upload_session",
    response_model=UploadSessionResponse,
    responses=PROBLEM_RESPONSES,
)
def create_unit_document_upload_session(
    body: CreateUploadSessionRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.DOCUMENTS_CREATE)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> UploadSessionResponse:
    del idempotency_key
    session = service.create_session(
        identity=identity,
        project_id=None,
        decision_unit_id=unit_id,
        filename=body.filename,
        file_size_bytes=body.file_size_bytes,
        declared_sha256=body.declared_sha256,
        content_type=body.content_type,
        kind=body.kind,
        chunk_size_bytes=body.chunk_size_bytes,
        request_id=request.state.request_id,
    )
    return _session_response(session)


@router.get(
    "/document-upload-sessions/{session_id}",
    operation_id="get_document_upload_session",
    response_model=UploadSessionResponse,
    responses=PROBLEM_RESPONSES,
)
def get_document_upload_session(
    session_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> UploadSessionResponse:
    return _session_response(service.get_session(identity=identity, session_id=session_id))


@router.put(
    "/document-upload-sessions/{session_id}/chunks/{part_number}",
    operation_id="put_document_upload_chunk",
    response_model=UploadSessionResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        }
    },
)
async def put_document_upload_chunk(
    request: Request,
    session_id: UUID,
    part_number: Annotated[int, Path(ge=1)],
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_PUT)),
    idempotency_key: str = Depends(require_idempotency_key),
    content_sha256: Annotated[str | None, Header(alias="X-Content-SHA256")] = None,
    service: DocumentIntakeService = Depends(get_intake_service),
) -> UploadSessionResponse:
    del idempotency_key
    data = await request.body()
    session = service.put_chunk(
        identity=identity,
        session_id=session_id,
        part_number=part_number,
        data=data,
        declared_chunk_sha256=content_sha256,
        request_id=request.state.request_id,
    )
    return _session_response(session)


@router.post(
    "/document-upload-sessions/{session_id}/complete",
    operation_id="complete_document_upload_session",
    response_model=CompleteUploadResponse,
    responses=PROBLEM_RESPONSES,
)
def complete_document_upload_session(
    request: Request,
    session_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.DOCUMENTS_COMPLETE)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> CompleteUploadResponse:
    del idempotency_key
    session, document = service.complete(
        identity=identity,
        session_id=session_id,
        request_id=request.state.request_id,
    )
    return CompleteUploadResponse(session=_session_response(session), document=document)


@router.post(
    "/document-upload-sessions/{session_id}/cancel",
    operation_id="cancel_document_upload_session",
    response_model=UploadSessionResponse,
    responses=PROBLEM_RESPONSES,
)
def cancel_document_upload_session(
    request: Request,
    session_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_CANCEL)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> UploadSessionResponse:
    del idempotency_key
    session = service.cancel(
        identity=identity,
        session_id=session_id,
        request_id=request.state.request_id,
    )
    return _session_response(session)


@router.get(
    "/projects/{project_id}/documents",
    operation_id="list_project_documents",
    response_model=DocumentListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_project_documents(
    project_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DocumentListResponse:
    return DocumentListResponse(
        items=service.list_documents(identity=identity, project_id=project_id)
    )


@router.get(
    "/decision-units/{unit_id}/documents",
    operation_id="list_unit_documents",
    response_model=DocumentListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_unit_documents(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DocumentListResponse:
    return DocumentListResponse(
        items=service.list_documents(identity=identity, decision_unit_id=unit_id)
    )


@router.get(
    "/documents/{document_id}",
    operation_id="get_document",
    response_model=SourceDocument,
    responses=PROBLEM_RESPONSES,
)
def get_document(
    document_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> SourceDocument:
    return service.get_document(identity=identity, document_id=document_id)


@router.post(
    "/documents/{document_id}/review",
    operation_id="review_document",
    response_model=SourceDocument,
    responses=PROBLEM_RESPONSES,
)
def review_document(
    request: Request,
    document_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_REVIEW)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> SourceDocument:
    del idempotency_key
    return service.review(
        identity=identity,
        document_id=document_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/documents/{document_id}/release-from-quarantine",
    operation_id="release_from_quarantine_document",
    response_model=SourceDocument,
    responses=PROBLEM_RESPONSES,
)
def release_from_quarantine_document(
    request: Request,
    document_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.DOCUMENTS_RELEASE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> SourceDocument:
    del idempotency_key
    return service.release(
        identity=identity,
        document_id=document_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/documents/{document_id}/quarantine",
    operation_id="quarantine_document",
    response_model=SourceDocument,
    responses=PROBLEM_RESPONSES,
)
def quarantine_document(
    request: Request,
    document_id: UUID,
    identity: IdentityContext = Depends(
        PermissionGuard(Permission.DOCUMENTS_QUARANTINE, mfa=True)
    ),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> SourceDocument:
    del idempotency_key
    return service.quarantine(
        identity=identity,
        document_id=document_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/documents/{document_id}/download",
    operation_id="download_document",
    responses={
        **PROBLEM_RESPONSES,
        200: {
            "description": "Document body",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
    },
)
def download_document(
    document_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> StreamingResponse:
    document, payload = service.download(identity=identity, document_id=document_id)
    filename = quote(document.source_filename or document.name)
    return StreamingResponse(
        io.BytesIO(payload),
        media_type=document.sniffed_content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/projects/{project_id}/parse-jobs",
    operation_id="create_project_parse_job",
    response_model=ParseJobResponse,
    responses=PROBLEM_RESPONSES,
)
def create_project_parse_job(
    body: CreateParseJobRequest,
    request: Request,
    project_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> ParseJobResponse:
    del idempotency_key
    return _parse_job_response(
        service.create_parse_job(
            identity=identity,
            document_id=body.document_id,
            project_id=project_id,
            decision_unit_id=None,
            request_id=request.state.request_id,
        )
    )


@router.post(
    "/decision-units/{unit_id}/parse-jobs",
    operation_id="create_unit_parse_job",
    response_model=ParseJobResponse,
    responses=PROBLEM_RESPONSES,
)
def create_unit_parse_job(
    body: CreateParseJobRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> ParseJobResponse:
    del idempotency_key
    return _parse_job_response(
        service.create_parse_job(
            identity=identity,
            document_id=body.document_id,
            project_id=None,
            decision_unit_id=unit_id,
            request_id=request.state.request_id,
        )
    )


@router.get(
    "/parse-jobs/{parse_job_id}",
    operation_id="get_parse_job",
    response_model=ParseJobResponse,
    responses=PROBLEM_RESPONSES,
)
def get_parse_job(
    parse_job_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> ParseJobResponse:
    return _parse_job_response(
        service.get_parse_job(identity=identity, job_id=parse_job_id)
    )


@router.post(
    "/parse-jobs/{parse_job_id}/retry",
    operation_id="retry_parse_job",
    response_model=ParseJobResponse,
    responses=PROBLEM_RESPONSES,
)
def retry_parse_job(
    request: Request,
    parse_job_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_RETRY)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> ParseJobResponse:
    del idempotency_key
    return _parse_job_response(
        service.retry_parse_job(
            identity=identity,
            job_id=parse_job_id,
            request_id=request.state.request_id,
        )
    )


@router.post(
    "/parse-jobs/{parse_job_id}/cancel",
    operation_id="cancel_parse_job",
    response_model=ParseJobResponse,
    responses=PROBLEM_RESPONSES,
)
def cancel_parse_job(
    request: Request,
    parse_job_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_CANCEL)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> ParseJobResponse:
    del idempotency_key
    return _parse_job_response(
        service.cancel_parse_job(
            identity=identity,
            job_id=parse_job_id,
            request_id=request.state.request_id,
        )
    )


@router.get(
    "/documents/{document_id}/derived-assets",
    operation_id="list_document_derived_assets",
    response_model=DerivedAssetListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_document_derived_assets(
    document_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DerivedAssetListResponse:
    return DerivedAssetListResponse(
        items=service.list_derived_assets(identity=identity, document_id=document_id)
    )


@router.get(
    "/derived-assets/{derived_asset_id}",
    operation_id="get_derived_asset",
    response_model=DerivedAsset,
    responses=PROBLEM_RESPONSES,
)
def get_derived_asset(
    derived_asset_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DerivedAsset:
    return service.get_derived_asset(identity=identity, asset_id=derived_asset_id)


@router.get(
    "/replicas",
    operation_id="list_replicas",
    response_model=ReplicaListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_replicas(
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_READ)),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> ReplicaListResponse:
    return ReplicaListResponse(items=service.list_replicas(identity=identity))


@router.post(
    "/document-links/inherit-to-unit",
    operation_id="inherit_to_unit_document_link",
    response_model=DocumentLink,
    responses=PROBLEM_RESPONSES,
)
def inherit_to_unit_document_link(
    body: InheritDocumentLinkRequest,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_INHERIT)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DocumentLink:
    del idempotency_key
    return service.inherit_to_unit(
        identity=identity,
        document_id=body.document_id,
        decision_unit_id=body.decision_unit_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )


@router.post(
    "/document-links/override",
    operation_id="override_document_link",
    response_model=DocumentLink,
    responses=PROBLEM_RESPONSES,
)
def override_document_link(
    body: OverrideDocumentLinkRequest,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_OVERRIDE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DocumentLink:
    del idempotency_key
    return service.override_link(
        identity=identity,
        document_id=body.document_id,
        decision_unit_id=body.decision_unit_id,
        reason=body.reason,
        priority=body.priority,
        request_id=request.state.request_id,
    )


@router.post(
    "/document-links/resolve-conflict",
    operation_id="resolve_conflict_document_link",
    response_model=DocumentLink,
    responses=PROBLEM_RESPONSES,
)
def resolve_conflict_document_link(
    body: ResolveConflictDocumentLinkRequest,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_RESOLVE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DocumentLink:
    del idempotency_key
    return service.resolve_conflict(
        identity=identity,
        link_id=body.link_id,
        chosen_document_id=body.chosen_document_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )


@router.post(
    "/document-links/detach",
    operation_id="detach_document_link",
    response_model=DocumentLink,
    responses=PROBLEM_RESPONSES,
)
def detach_document_link(
    body: DetachDocumentLinkRequest,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.DOCUMENTS_DETACH)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DocumentIntakeService = Depends(get_intake_service),
) -> DocumentLink:
    del idempotency_key
    return service.detach_link(
        identity=identity,
        link_id=body.link_id,
        request_id=request.state.request_id,
    )
