"""Contract tests for the member-3 FR-02 document intake API."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from conftest import DOMAIN_A, TENANT_A, StaticAuthenticator
from fastapi.testclient import TestClient

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.main import create_app
from biaice.modules.documents.application.services import (
    DEFAULT_CHUNK_SIZE_BYTES,
)
from biaice.modules.documents.infrastructure.scanner import EICAR_SIGNATURE

NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"
PDF_HASH = hashlib.sha256(PDF_BYTES).hexdigest()
UPLOADER = UUID("00000000-0000-4000-8000-000000000031")
CHECKER = UUID("00000000-0000-4000-8000-000000000032")


def _identity(
    *,
    actor: UUID = UPLOADER,
    roles: frozenset[Role] = frozenset({Role.DOCUMENT_SPECIALIST}),
    mfa: bool = True,
    tenant=TENANT_A,
    domain=DOMAIN_A,
    all_projects: bool = True,
    all_decision_units: bool = True,
    project_ids: frozenset = frozenset(),
    decision_unit_ids: frozenset = frozenset(),
) -> IdentityContext:
    return IdentityContext(
        subject_id=actor,
        username="m3",
        display_name="Member Three",
        roles=roles,
        scope=TenantScope(
            tenant_id=tenant,
            data_domain_id=domain,
            all_projects=all_projects,
            all_decision_units=all_decision_units,
            project_ids=project_ids,
            decision_unit_ids=decision_unit_ids,
        ),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


def _app(identity: IdentityContext | None = None):
    identity = identity or _identity()
    settings = Settings(
        environment="test",
        deployment_profile="synthetic_http",
        real_data_mode_requested=False,
        byok_enabled=False,
        allow_test_auth=True,
        audit_sink_required=False,
        audit_anchor_required=False,
        migrations_required=False,
        oidc_jwks_url=None,
        oidc_issuer=None,
    )
    return create_app(
        settings=settings,
        authenticator=StaticAuthenticator(identity),
        audit_writer=HashChainAuditWriter(InMemoryAppendOnlyAuditSink()),
    )


def _client(identity: IdentityContext | None = None) -> TestClient:
    client = TestClient(_app(identity))
    client.headers["Authorization"] = "Bearer test-token"
    return client


def _idem(suffix: str = "upload") -> str:
    return f"idempotency-key-test-{suffix}-123456"


def _create_body(**overrides):
    body = {
        "filename": "tender.pdf",
        "file_size_bytes": len(PDF_BYTES),
        "declared_sha256": PDF_HASH,
        "content_type": "application/pdf",
        "kind": "TENDER",
        "chunk_size_bytes": DEFAULT_CHUNK_SIZE_BYTES,
    }
    body.update(overrides)
    return body


def _put_chunk(client: TestClient, session_id: str, data: bytes = PDF_BYTES):
    return client.put(
        f"/api/v1/document-upload-sessions/{session_id}/chunks/1",
        content=data,
        headers={
            "Idempotency-Key": _idem("chunk"),
            "Content-Type": "application/octet-stream",
            "X-Content-SHA256": hashlib.sha256(data).hexdigest(),
        },
    )


@pytest.fixture
def client():
    return _client()


def test_list_project_documents_returns_empty(client):
    project = uuid4()
    response = client.get(f"/api/v1/projects/{project}/documents")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_create_upload_session_requires_idempotency(client):
    project = uuid4()
    response = client.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_upload_complete_review_and_independent_release(client):
    project = uuid4()
    created = client.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(),
        headers={"Idempotency-Key": _idem("create")},
    )
    assert created.status_code == 200, created.text
    session = created.json()
    assert session["status"] == "ACTIVE"
    assert session["next_action"] == "UPLOAD_CHUNK"
    assert session["missing_part_numbers"] == [1]

    chunked = _put_chunk(client, session["session_id"])
    assert chunked.status_code == 200, chunked.text
    assert chunked.json()["next_action"] == "COMPLETE"

    completed = client.post(
        f"/api/v1/document-upload-sessions/{session['session_id']}/complete",
        headers={"Idempotency-Key": _idem("complete")},
    )
    assert completed.status_code == 200, completed.text
    document = completed.json()["document"]
    assert document["status"] == "SCAN_PASSED"
    document_id = document["document_id"]

    reviewed = client.post(
        f"/api/v1/documents/{document_id}/review",
        headers={"Idempotency-Key": _idem("review")},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "UNDER_REVIEW"

    forbidden = client.post(
        f"/api/v1/documents/{document_id}/release-from-quarantine",
        headers={"Idempotency-Key": _idem("self-release")},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "PERMISSION_DENIED"

    checker = _client(_identity(actor=CHECKER, roles=frozenset({Role.DOCUMENT_STEWARD})))
    # Separate app/state: the document lives on the first app. Reuse the first
    # app by swapping identity is not available, so release through the same
    # process requires sharing repository. Use the first client only after
    # granting release on a shared app in the next test.
    listed = client.get(f"/api/v1/projects/{project}/documents")
    assert listed.status_code == 200
    assert [item["document_id"] for item in listed.json()["items"]] == [document_id]
    fetched = client.get(f"/api/v1/documents/{document_id}")
    assert fetched.status_code == 200
    assert fetched.json()["content_hash"] == PDF_HASH
    del checker


def test_independent_release_on_shared_app():
    uploader = _identity()
    app = _app(uploader)
    specialist = TestClient(app)
    specialist.headers["Authorization"] = "Bearer test-token"
    project = uuid4()
    session = specialist.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(),
        headers={"Idempotency-Key": _idem("create")},
    ).json()
    _put_chunk(specialist, session["session_id"])
    document_id = specialist.post(
        f"/api/v1/document-upload-sessions/{session['session_id']}/complete",
        headers={"Idempotency-Key": _idem("complete")},
    ).json()["document"]["document_id"]
    specialist.post(
        f"/api/v1/documents/{document_id}/review",
        headers={"Idempotency-Key": _idem("review")},
    )

    app.state.authenticator = StaticAuthenticator(
        _identity(actor=CHECKER, roles=frozenset({Role.DOCUMENT_STEWARD}))
    )
    steward = TestClient(app)
    steward.headers["Authorization"] = "Bearer test-token"
    released = steward.post(
        f"/api/v1/documents/{document_id}/release-from-quarantine",
        headers={"Idempotency-Key": _idem("release")},
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "RELEASED"
    assert released.json()["released_by"] == str(CHECKER)


def test_blocked_extension_and_eicar_are_fail_closed(client):
    project = uuid4()
    blocked = client.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(filename="malware.exe"),
        headers={"Idempotency-Key": _idem("exe")},
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "DOCUMENT_TYPE_BLOCKED"

    eicar_hash = hashlib.sha256(EICAR_SIGNATURE).hexdigest()
    session = client.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(
            filename="eicar.pdf",
            file_size_bytes=len(EICAR_SIGNATURE),
            declared_sha256=eicar_hash,
        ),
        headers={"Idempotency-Key": _idem("eicar")},
    ).json()
    _put_chunk(client, session["session_id"], EICAR_SIGNATURE)
    completed = client.post(
        f"/api/v1/document-upload-sessions/{session['session_id']}/complete",
        headers={"Idempotency-Key": _idem("eicar-complete")},
    )
    assert completed.status_code == 200
    document = completed.json()["document"]
    assert document["status"] == "SCAN_FAILED"
    assert document["scan_result"] == "INFECTED"
    review = client.post(
        f"/api/v1/documents/{document['document_id']}/review",
        headers={"Idempotency-Key": _idem("eicar-review")},
    )
    assert review.status_code == 409
    assert review.json()["code"] == "DOCUMENT_SCAN_FAILED"


def test_create_requires_permission_and_release_requires_mfa():
    project = uuid4()
    auditor = _client(_identity(roles=frozenset({Role.AUDITOR})))
    denied = auditor.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(),
        headers={"Idempotency-Key": _idem("auditor")},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "PERMISSION_DENIED"

    mfa_client = _client(
        _identity(actor=CHECKER, roles=frozenset({Role.DOCUMENT_STEWARD}), mfa=False)
    )
    response = mfa_client.post(
        f"/api/v1/documents/{uuid4()}/release-from-quarantine",
        headers={"Idempotency-Key": _idem("mfa")},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "MFA_REQUIRED"


def test_scope_violation_looks_like_missing_resource():
    allowed = uuid4()
    other = uuid4()
    client = _client(
        _identity(
            all_projects=False,
            project_ids=frozenset({allowed}),
        )
    )
    response = client.post(
        f"/api/v1/projects/{other}/document-upload-sessions",
        json=_create_body(),
        headers={"Idempotency-Key": _idem("scope")},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "TENANT_SCOPE_VIOLATION"


def _upload_pdf(client: TestClient, project: UUID, filename: str = "tender.pdf"):
    session = client.post(
        f"/api/v1/projects/{project}/document-upload-sessions",
        json=_create_body(filename=filename),
        headers={"Idempotency-Key": _idem(f"create-{filename}")},
    ).json()
    _put_chunk(client, session["session_id"])
    completed = client.post(
        f"/api/v1/document-upload-sessions/{session['session_id']}/complete",
        headers={"Idempotency-Key": _idem(f"complete-{filename}")},
    )
    assert completed.status_code == 200, completed.text
    return completed.json()["document"]


def test_download_parse_and_replicas(client):
    project = uuid4()
    document = _upload_pdf(client, project)
    denied = client.get(f"/api/v1/documents/{uuid4()}/download")
    assert denied.status_code == 404

    body = client.get(f"/api/v1/documents/{document['document_id']}/download")
    assert body.status_code == 200
    assert body.content == PDF_BYTES

    created = client.post(
        f"/api/v1/projects/{project}/parse-jobs",
        json={"document_id": document["document_id"]},
        headers={"Idempotency-Key": _idem("parse")},
    )
    assert created.status_code == 200, created.text
    job = created.json()
    assert job["status"] == "SUCCEEDED"
    assert job["progress_percent"] == 100
    polled = client.get(f"/api/v1/parse-jobs/{job['parse_job_id']}")
    assert polled.status_code == 200
    assert polled.json()["status"] == "SUCCEEDED"

    assets = client.get(f"/api/v1/documents/{document['document_id']}/derived-assets")
    assert assets.status_code == 200
    assert len(assets.json()["items"]) == 1
    asset_id = assets.json()["items"][0]["asset_id"]
    fetched = client.get(f"/api/v1/derived-assets/{asset_id}")
    assert fetched.status_code == 200
    assert fetched.json()["fragment_ref"].startswith("doc:")

    replicas = client.get("/api/v1/replicas")
    assert replicas.status_code == 200
    assert len(replicas.json()["items"]) >= 2


def test_document_link_inherit_and_detach(client):
    project = uuid4()
    unit = uuid4()
    document = _upload_pdf(client, project)
    inherited = client.post(
        "/api/v1/document-links/inherit-to-unit",
        json={"document_id": document["document_id"], "decision_unit_id": str(unit)},
        headers={"Idempotency-Key": _idem("inherit")},
    )
    assert inherited.status_code == 200, inherited.text
    assert inherited.json()["relation"] == "INHERITED"
    listed = client.get(f"/api/v1/decision-units/{unit}/documents")
    assert listed.status_code == 200
    assert [item["document_id"] for item in listed.json()["items"]] == [document["document_id"]]
    detached = client.post(
        "/api/v1/document-links/detach",
        json={"link_id": inherited.json()["link_id"]},
        headers={"Idempotency-Key": _idem("detach")},
    )
    assert detached.status_code == 200
    empty = client.get(f"/api/v1/decision-units/{unit}/documents")
    assert empty.json()["items"] == []
