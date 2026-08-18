"""Unit tests for the member-3 FR-02 document intake service."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.errors import BiaiceError
from biaice.modules.documents.application.repository import InMemoryDocumentsRepository
from biaice.modules.documents.application.services import (
    DEFAULT_CHUNK_SIZE_BYTES,
    DocumentIntakeService,
)
from biaice.modules.documents.domain.models import (
    DocumentKind,
    DocumentStatus,
    ScanResult,
    UploadSessionStatus,
)
from biaice.modules.documents.infrastructure.scanner import EICAR_SIGNATURE

TENANT = uuid4()
DOMAIN = uuid4()
PROJECT = uuid4()
UNIT = uuid4()
UPLOADER = uuid4()
REVIEWER = uuid4()
NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _identity(*, actor=UPLOADER, mfa: bool = True, tenant=TENANT, domain=DOMAIN):
    return IdentityContext(
        subject_id=actor,
        username="m3",
        display_name="Member Three",
        roles=frozenset({Role.DOCUMENT_SPECIALIST}),
        scope=TenantScope(
            tenant_id=tenant,
            data_domain_id=domain,
            all_projects=True,
            all_decision_units=True,
        ),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


def _service(
    now: datetime | None = None,
    repository: InMemoryDocumentsRepository | None = None,
) -> tuple[
    DocumentIntakeService,
    HashChainAuditWriter,
    InMemoryAppendOnlyAuditSink,
    InMemoryDocumentsRepository,
]:
    sink = InMemoryAppendOnlyAuditSink()
    audit = HashChainAuditWriter(sink, clock=FixedClock(now or NOW))
    repository = repository or InMemoryDocumentsRepository()
    service = DocumentIntakeService(
        repository=repository,
        clock=FixedClock(now or NOW),
        audit_writer=audit,
        outbox_port=None,
    )
    return service, audit, sink, repository


def _complete_payload(
    service: DocumentIntakeService,
    payload: bytes,
    *,
    filename: str = "tender.pdf",
    identity=None,
    project_id=PROJECT,
    decision_unit_id=None,
):
    identity = identity or _identity()
    digest = hashlib.sha256(payload).hexdigest()
    session = service.create_session(
        identity=identity,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        filename=filename,
        file_size_bytes=len(payload),
        declared_sha256=digest,
        content_type="application/pdf",
        kind=DocumentKind.TENDER,
        chunk_size_bytes=DEFAULT_CHUNK_SIZE_BYTES,
        request_id="req-1",
    )
    service.put_chunk(
        identity=identity,
        session_id=session.session_id,
        part_number=1,
        data=payload,
        declared_chunk_sha256=digest,
        request_id="req-2",
    )
    return service.complete(identity=identity, session_id=session.session_id, request_id="req-3")


def test_complete_pdf_upload_scans_clean_and_is_not_released() -> None:
    service, _, sink, _ = _service()
    identity = _identity()
    completed, document = _complete_payload(service, PDF_BYTES, identity=identity)

    assert completed.status is UploadSessionStatus.COMPLETED
    assert document.status is DocumentStatus.SCAN_PASSED
    assert document.scan_result is ScanResult.CLEAN
    assert document.content_hash == hashlib.sha256(PDF_BYTES).hexdigest()
    actions = [event.action for event in sink.list_events(identity.scope)]
    assert "documents.source_document.upload" in actions


def test_blocked_extension_is_rejected_before_bytes_are_accepted() -> None:
    service, _, _, _ = _service()
    with pytest.raises(BiaiceError) as error:
        service.create_session(
            identity=_identity(),
            project_id=PROJECT,
            decision_unit_id=None,
            filename="payload.exe",
            file_size_bytes=12,
            declared_sha256="a" * 64,
            content_type="application/octet-stream",
            kind=DocumentKind.TENDER,
            chunk_size_bytes=12,
            request_id="req-1",
        )
    assert error.value.code == "DOCUMENT_TYPE_BLOCKED"


def test_eicar_payload_stays_quarantined_and_cannot_be_reviewed() -> None:
    service, _, _, _ = _service()
    _, document = _complete_payload(service, EICAR_SIGNATURE, filename="eicar.pdf")
    assert document.status is DocumentStatus.SCAN_FAILED
    assert document.scan_result is ScanResult.INFECTED
    with pytest.raises(BiaiceError) as error:
        service.review(identity=_identity(), document_id=document.document_id, request_id="req-4")
    assert error.value.code == "DOCUMENT_SCAN_FAILED"


def test_release_requires_review_and_independent_checker() -> None:
    service, _, sink, _ = _service()
    identity = _identity()
    _, document = _complete_payload(
        service,
        PDF_BYTES,
        identity=identity,
        project_id=None,
        decision_unit_id=UNIT,
    )
    with pytest.raises(BiaiceError) as not_reviewable:
        service.release(
            identity=_identity(actor=REVIEWER),
            document_id=document.document_id,
            request_id="req-4",
        )
    assert not_reviewable.value.code == "DOCUMENT_NOT_RELEASABLE"

    reviewed = service.review(
        identity=identity, document_id=document.document_id, request_id="req-5"
    )
    assert reviewed.status is DocumentStatus.UNDER_REVIEW
    with pytest.raises(BiaiceError) as maker:
        service.release(identity=identity, document_id=document.document_id, request_id="req-6")
    assert maker.value.code == "MAKER_CHECKER_REQUIRED"

    released = service.release(
        identity=_identity(actor=REVIEWER),
        document_id=document.document_id,
        request_id="req-7",
    )
    assert released.status is DocumentStatus.RELEASED
    assert released.released_by == REVIEWER
    actions = [event.action for event in sink.list_events(identity.scope)]
    assert "documents.source_document.release" in actions


def test_expired_session_rejects_further_chunks() -> None:
    service, _, _, repository = _service()
    identity = _identity()
    digest = hashlib.sha256(PDF_BYTES).hexdigest()
    session = service.create_session(
        identity=identity,
        project_id=PROJECT,
        decision_unit_id=None,
        filename="tender.pdf",
        file_size_bytes=len(PDF_BYTES),
        declared_sha256=digest,
        content_type="application/pdf",
        kind=DocumentKind.TENDER,
        chunk_size_bytes=DEFAULT_CHUNK_SIZE_BYTES,
        request_id="req-1",
    )
    later, _, _, _ = _service(now=NOW + timedelta(hours=25), repository=repository)
    with pytest.raises(BiaiceError) as error:
        later.put_chunk(
            identity=identity,
            session_id=session.session_id,
            part_number=1,
            data=PDF_BYTES,
            declared_chunk_sha256=digest,
            request_id="req-2",
        )
    assert error.value.code == "UPLOAD_SESSION_EXPIRED"


def test_scope_isolation_hides_other_tenants() -> None:
    service, _, _, _ = _service()
    identity = _identity()
    digest = hashlib.sha256(PDF_BYTES).hexdigest()
    session = service.create_session(
        identity=identity,
        project_id=PROJECT,
        decision_unit_id=None,
        filename="tender.pdf",
        file_size_bytes=len(PDF_BYTES),
        declared_sha256=digest,
        content_type="application/pdf",
        kind=DocumentKind.TENDER,
        chunk_size_bytes=DEFAULT_CHUNK_SIZE_BYTES,
        request_id="req-1",
    )
    other = _identity(tenant=uuid4())
    with pytest.raises(BiaiceError) as error:
        service.get_session(identity=other, session_id=session.session_id)
    assert error.value.code == "RESOURCE_NOT_FOUND"


def test_cancel_is_idempotent_and_drops_partial_parts() -> None:
    service, _, _, _ = _service()
    identity = _identity()
    digest = hashlib.sha256(PDF_BYTES).hexdigest()
    session = service.create_session(
        identity=identity,
        project_id=PROJECT,
        decision_unit_id=None,
        filename="tender.pdf",
        file_size_bytes=len(PDF_BYTES),
        declared_sha256=digest,
        content_type="application/pdf",
        kind=DocumentKind.TENDER,
        chunk_size_bytes=DEFAULT_CHUNK_SIZE_BYTES,
        request_id="req-1",
    )
    service.put_chunk(
        identity=identity,
        session_id=session.session_id,
        part_number=1,
        data=PDF_BYTES,
        declared_chunk_sha256=digest,
        request_id="req-2",
    )
    cancelled = service.cancel(identity=identity, session_id=session.session_id, request_id="req-3")
    again = service.cancel(identity=identity, session_id=session.session_id, request_id="req-4")
    assert cancelled.status is UploadSessionStatus.CANCELLED
    assert again.status is UploadSessionStatus.CANCELLED
    with pytest.raises(BiaiceError) as error:
        service.complete(identity=identity, session_id=session.session_id, request_id="req-5")
    assert error.value.code == "UPLOAD_SESSION_NOT_ACTIVE"


def test_content_hash_dedup_reuses_existing_document_and_persists_blob() -> None:
    service, _, _, repository = _service()
    _, first = _complete_payload(service, PDF_BYTES)
    _, second = _complete_payload(service, PDF_BYTES, filename="copy.pdf")
    assert first.document_id == second.document_id
    assert repository.get_blob(first.storage_key) == PDF_BYTES
    assert service.list_replicas(identity=_identity())


def test_download_denied_for_infected_payload() -> None:
    service, _, _, _ = _service()
    _, infected = _complete_payload(service, EICAR_SIGNATURE, filename="eicar.pdf")
    with pytest.raises(BiaiceError) as error:
        service.download(identity=_identity(), document_id=infected.document_id)
    assert error.value.code == "DOCUMENT_NOT_DOWNLOADABLE"
    _, clean = _complete_payload(service, PDF_BYTES)
    document, payload = service.download(identity=_identity(), document_id=clean.document_id)
    assert document.document_id == clean.document_id
    assert payload == PDF_BYTES


def test_parse_pdf_registers_derived_asset_and_image_requires_manual_entry() -> None:
    service, _, _, _ = _service()
    identity = _identity()
    pdf = b"%PDF-1.4\nBT\n(Hello tender)\nET\n%%EOF\n"
    _, document = _complete_payload(service, pdf, identity=identity)
    job = service.create_parse_job(
        identity=identity,
        document_id=document.document_id,
        project_id=PROJECT,
        decision_unit_id=None,
        request_id="req-parse",
    )
    assert job.status.value == "SUCCEEDED"
    assert job.progress_percent == 100
    assets = service.list_derived_assets(identity=identity, document_id=document.document_id)
    assert len(assets) == 1
    assert "Hello tender" in (service.repository.get_blob(assets[0].storage_key) or b"").decode()

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
    _, image = _complete_payload(service, png, filename="scan.png", identity=identity)
    failed = service.create_parse_job(
        identity=identity,
        document_id=image.document_id,
        project_id=PROJECT,
        decision_unit_id=None,
        request_id="req-ocr",
    )
    assert failed.status.value == "FAILED"
    assert failed.retryable is not None
    assert failed.retryable.value == "NO_MANUAL_ENTRY_REQUIRED"
    with pytest.raises(BiaiceError) as error:
        service.retry_parse_job(identity=identity, job_id=failed.job_id, request_id="req-retry")
    assert error.value.code == "JOB_NOT_RETRYABLE"


def test_cancel_queued_parse_job() -> None:
    service, _, _, _ = _service()
    identity = _identity()
    _, document = _complete_payload(service, PDF_BYTES, identity=identity)
    job = service.create_parse_job(
        identity=identity,
        document_id=document.document_id,
        project_id=PROJECT,
        decision_unit_id=None,
        request_id="req-q",
        execute=False,
    )
    cancelled = service.cancel_parse_job(identity=identity, job_id=job.job_id, request_id="req-c")
    assert cancelled.status.value == "CANCELLED"


def test_inherit_override_conflict_requires_human_resolve() -> None:
    service, _, _, _ = _service()
    identity = _identity()
    _, project_doc = _complete_payload(service, PDF_BYTES, identity=identity)
    other_pdf = b"%PDF-1.4\nBT\n(Unit override)\nET\n%%EOF\n"
    _, unit_doc = _complete_payload(
        service,
        other_pdf,
        filename="unit.pdf",
        identity=identity,
        project_id=None,
        decision_unit_id=UNIT,
    )
    inherited = service.inherit_to_unit(
        identity=identity,
        document_id=project_doc.document_id,
        decision_unit_id=UNIT,
        reason=None,
        request_id="req-in",
    )
    assert inherited.relation.value == "INHERITED"
    override = service.override_link(
        identity=identity,
        document_id=unit_doc.document_id,
        decision_unit_id=UNIT,
        reason="unit-specific annex",
        priority=2,
        request_id="req-ov",
    )
    assert override.conflict_state.value == "OPEN"
    listed = service.list_documents(identity=identity, decision_unit_id=UNIT)
    assert {item.document_id for item in listed} == {
        project_doc.document_id,
        unit_doc.document_id,
    }
    resolved = service.resolve_conflict(
        identity=_identity(actor=REVIEWER),
        link_id=override.link_id,
        chosen_document_id=unit_doc.document_id,
        reason="unit annex supersedes inherited tender",
        request_id="req-rs",
    )
    assert resolved.conflict_state.value == "RESOLVED"
    remaining = service.list_documents(identity=identity, decision_unit_id=UNIT)
    assert [item.document_id for item in remaining] == [unit_doc.document_id]


def test_read_port_hides_unreleased_documents() -> None:
    from biaice.modules.documents.application.services import DocumentReadService

    service, _, _, repository = _service()
    identity = _identity()
    _, document = _complete_payload(service, PDF_BYTES, identity=identity)
    port = DocumentReadService(repository)
    assert (
        port.get_released_document(scope=identity.scope, document_id=document.document_id) is None
    )
    service.review(identity=identity, document_id=document.document_id, request_id="r")
    released = service.release(
        identity=_identity(actor=REVIEWER),
        document_id=document.document_id,
        request_id="rel",
    )
    view = port.get_released_document(scope=identity.scope, document_id=released.document_id)
    assert view is not None
    assert view.content_hash == released.content_hash
