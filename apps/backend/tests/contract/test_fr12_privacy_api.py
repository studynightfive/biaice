"""Contract and policy tests for the member-5 FR-12 synthetic slice."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from biaice.api.market_privacy import FR12_IMPLEMENTED_OPERATION_IDS
from biaice.core.audit import (
    HashChainAuditWriter,
    InMemoryAppendOnlyAuditSink,
    UnavailableAuditWriter,
)
from biaice.core.auth import Authenticator, IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.main import create_app

NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
TENANT_A = UUID("00000000-0000-4000-8000-000000000301")
TENANT_B = UUID("00000000-0000-4000-8000-000000000302")
DOMAIN_A = UUID("00000000-0000-4000-8000-000000000311")

RESOURCES = (
    ("processing-records", "processing_record_id"),
    ("legal-basis-evidence", "legal_basis_evidence_id"),
    ("notice-consent-records", "notice_consent_record_id"),
    ("pia-records", "pia_record_id"),
    ("cross-border-assessments", "cross_border_assessment_id"),
    ("provider-policies", "provider_policie_id"),
    ("dsr-policies", "dsr_policie_id"),
    ("load-profiles", "load_profile_id"),
    ("data-subject-requests", "data_subject_request_id"),
    ("incident-policies", "incident_policie_id"),
    ("incidents", "incident_id"),
)


class SwitchingAuthenticator(Authenticator):
    def __init__(self, identity: IdentityContext) -> None:
        self.identity = identity

    def authenticate(self, token: str) -> IdentityContext:
        assert token
        return self.identity


def _identity(
    *,
    tenant_id: UUID = TENANT_A,
    subject_id: UUID | None = None,
    roles: frozenset[Role] = frozenset({Role.PRIVACY_OFFICER}),
    mfa: bool = True,
) -> IdentityContext:
    return IdentityContext(
        subject_id=subject_id or uuid4(),
        username="m5-privacy",
        display_name="Member Five Privacy",
        roles=roles,
        scope=TenantScope(
            tenant_id=tenant_id,
            data_domain_id=DOMAIN_A,
            all_projects=True,
            all_decision_units=True,
        ),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


def _app(
    authenticator: Authenticator,
    *,
    audit_writer=None,
):
    return create_app(
        settings=Settings(
            environment="test",
            allow_test_auth=True,
            migrations_required=False,
            audit_sink_required=False,
            audit_anchor_required=False,
            cursor_hmac_key="fr12-test-cursor-key-0000000000000000",
        ),
        authenticator=authenticator,
        audit_writer=audit_writer or HashChainAuditWriter(InMemoryAppendOnlyAuditSink()),
    )


@pytest.fixture
def api():
    maker = _identity(subject_id=UUID("00000000-0000-4000-8000-000000000321"))
    checker = _identity(subject_id=UUID("00000000-0000-4000-8000-000000000322"))
    authenticator = SwitchingAuthenticator(maker)
    with TestClient(_app(authenticator)) as client:
        client.headers["Authorization"] = "Bearer fr12-test-token"
        yield client, authenticator, maker, checker


_keys = count(1)


def _idem(prefix: str = "fr12") -> str:
    return f"{prefix}-{next(_keys):012d}"


def _create(client: TestClient, resource: str, *, key: str | None = None) -> dict:
    response = client.post(
        f"/api/v1/{resource}",
        headers={"Idempotency-Key": key or _idem("create")},
        json={
            "subject_scope": "synthetic-fixture",
            "justification_ref": "policy://fr12/test",
            "retention_days": 30,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _action(
    client: TestClient,
    resource: str,
    resource_id: str,
    action: str,
    *,
    body: dict | None = None,
) -> dict:
    response = client.post(
        f"/api/v1/{resource}/{resource_id}/{action}",
        headers={"Idempotency-Key": _idem(action.replace("-", ""))},
        json=body or {},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_openapi_exposes_all_fr12_operations_as_real_synthetic_handlers() -> None:
    schema = _app(SwitchingAuthenticator(_identity())).openapi()
    operations = {
        operation["operationId"]: (path, method, operation)
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if isinstance(operation, dict) and operation.get("x-fr") == "FR-12"
    }
    assert set(operations) == FR12_IMPLEMENTED_OPERATION_IDS
    assert len(operations) == 53
    assert all(item[2]["x-contract-only"] is False for item in operations.values())
    command_schema = schema["components"]["schemas"]["MarketResourceCommand"]
    assert command_schema["additionalProperties"] is False
    assert "api_key" not in command_schema["properties"]
    assert "tenant_id" not in command_schema["properties"]
    assert operations["get_provider_policie"][0] == (
        "/api/v1/provider-policies/{provider_policie_id}"
    )
    assert operations["get_dsr_policie"][0] == "/api/v1/dsr-policies/{dsr_policie_id}"
    assert operations["get_incident_policie"][0] == (
        "/api/v1/incident-policies/{incident_policie_id}"
    )
    assert (
        "/api/v1/cross_border_assessments/{cross_border_assessment_id}/mark-not-required"
        not in schema["paths"]
    )


def test_all_collection_create_list_and_get_routes_work(api) -> None:
    client, _, _, _ = api
    for resource, _ in RESOURCES:
        created = _create(client, resource)
        listed = client.get(f"/api/v1/{resource}")
        assert listed.status_code == 200, listed.text
        assert created["resource_id"] in {item["resource_id"] for item in listed.json()["items"]}
        fetched = client.get(f"/api/v1/{resource}/{created['resource_id']}")
        assert fetched.status_code == 200, fetched.text
        assert fetched.json() == created


def test_create_is_idempotent_and_rejects_key_reuse_with_different_body(api) -> None:
    client, _, _, _ = api
    key = _idem("idempotent")
    body = {"subject_scope": "synthetic", "retention_days": 7}
    first = client.post(
        "/api/v1/legal-basis-evidence",
        headers={"Idempotency-Key": key},
        json=body,
    )
    replay = client.post(
        "/api/v1/legal-basis-evidence",
        headers={"Idempotency-Key": key},
        json=body,
    )
    conflict = client.post(
        "/api/v1/legal-basis-evidence",
        headers={"Idempotency-Key": key},
        json={**body, "retention_days": 8},
    )
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_scope_secret_permission_and_audit_boundaries_fail_closed(api) -> None:
    client, authenticator, maker, _ = api
    missing_key = client.post("/api/v1/legal-basis-evidence", json={})
    scope_spoof = client.post(
        "/api/v1/legal-basis-evidence",
        headers={"Idempotency-Key": _idem("scope")},
        json={"nested": {"tenant_id": str(TENANT_B)}},
    )
    secret = client.post(
        "/api/v1/legal-basis-evidence",
        headers={"Idempotency-Key": _idem("secret")},
        json={"apiKey": "never-store-this"},
    )
    authenticator.identity = maker.model_copy(update={"roles": frozenset({Role.BID_MANAGER})})
    denied = client.get("/api/v1/legal-basis-evidence")
    assert missing_key.status_code == 400
    assert missing_key.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert scope_spoof.status_code == secret.status_code == 422
    assert "never-store-this" not in secret.text
    assert denied.status_code == 403
    assert denied.json()["code"] == "PERMISSION_DENIED"

    unavailable = TestClient(
        _app(
            SwitchingAuthenticator(maker),
            audit_writer=UnavailableAuditWriter(),
        )
    )
    blocked = unavailable.post(
        "/api/v1/legal-basis-evidence",
        headers={
            "Authorization": "Bearer fr12-test-token",
            "Idempotency-Key": _idem("audit"),
        },
        json={},
    )
    assert blocked.status_code == 503
    assert blocked.json()["code"] == "AUDIT_UNAVAILABLE"


def test_cross_tenant_record_is_hidden(api) -> None:
    client, authenticator, _, _ = api
    created = _create(client, "legal-basis-evidence")
    authenticator.identity = _identity(tenant_id=TENANT_B)
    response = client.get(f"/api/v1/legal-basis-evidence/{created['resource_id']}")
    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"


def test_all_action_routes_enforce_lifecycle_and_return_state(api) -> None:
    client, authenticator, maker, checker = api

    def created(resource: str) -> dict:
        authenticator.identity = maker
        return _create(client, resource)

    def checked_action(
        resource: str,
        item: dict,
        action: str,
        *,
        body: dict | None = None,
    ) -> dict:
        authenticator.identity = checker
        return _action(
            client,
            resource,
            item["resource_id"],
            action,
            body=body,
        )

    pia = checked_action("pia-records", created("pia-records"), "approve")
    assert pia["state"] == "APPROVED"
    assert checked_action("pia-records", pia, "revoke")["state"] == "REVOKED"

    cross = checked_action(
        "cross-border-assessments",
        created("cross-border-assessments"),
        "approve",
    )
    assert checked_action("cross-border-assessments", cross, "expire")["state"] == "EXPIRED"
    cross_not_required = checked_action(
        "cross-border-assessments",
        created("cross-border-assessments"),
        "mark-not-required",
        body={"reason_code": "VERIFIED_NO_CROSS_BORDER"},
    )
    assert cross_not_required["state"] == "NOT_REQUIRED"
    assert (
        checked_action("cross-border-assessments", cross_not_required, "revoke")["state"]
        == "REVOKED"
    )

    provider = checked_action("provider-policies", created("provider-policies"), "approve")
    assert checked_action("provider-policies", provider, "expire")["state"] == ("EXPIRED")
    provider_not_required = checked_action(
        "provider-policies",
        created("provider-policies"),
        "mark-not-required",
        body={"reason_code": "VERIFIED_PROVIDER_NOT_USED"},
    )
    assert (
        checked_action("provider-policies", provider_not_required, "revoke")["state"] == "REVOKED"
    )

    dsr_policy = checked_action("dsr-policies", created("dsr-policies"), "publish")
    assert checked_action("dsr-policies", dsr_policy, "archive")["state"] == ("ARCHIVED")
    assert checked_action("load-profiles", created("load-profiles"), "freeze")["state"] == "FROZEN"

    request = checked_action(
        "data-subject-requests",
        created("data-subject-requests"),
        "verify-identity",
    )
    request = checked_action(
        "data-subject-requests",
        request,
        "transition",
        body={"target_state": "IN_PROGRESS"},
    )
    request = checked_action(
        "data-subject-requests",
        request,
        "transition",
        body={"target_state": "READY_TO_COMPLETE"},
    )
    assert checked_action("data-subject-requests", request, "complete")["state"] == "COMPLETED"

    assert (
        checked_action("incident-policies", created("incident-policies"), "approve")["state"]
        == "APPROVED"
    )
    incident = created("incidents")
    for target in ("TRIAGED", "CONTAINED", "REMEDIATING", "RESOLVED"):
        incident = checked_action(
            "incidents",
            incident,
            "transition",
            body={"target_state": target},
        )
    assert checked_action("incidents", incident, "close")["state"] == "CLOSED"

    authenticator.identity = maker
    withdrawal = client.post(
        "/api/v1/consent-withdrawals",
        headers={"Idempotency-Key": _idem("withdraw")},
        json={"notice_ref": "notice://synthetic/1"},
    )
    assert withdrawal.status_code == 200
    assert withdrawal.json()["state"] == "RECORDED"


def test_maker_checker_mfa_and_invalid_transition_are_rejected(api) -> None:
    client, authenticator, maker, checker = api
    pia = _create(client, "pia-records")
    same_maker = client.post(
        f"/api/v1/pia-records/{pia['resource_id']}/approve",
        headers={"Idempotency-Key": _idem("maker")},
        json={},
    )
    assert same_maker.status_code == 409
    assert same_maker.json()["code"] == "MAKER_CHECKER_REQUIRED"

    authenticator.identity = checker.model_copy(update={"mfa_verified": False})
    no_mfa = client.post(
        f"/api/v1/pia-records/{pia['resource_id']}/approve",
        headers={"Idempotency-Key": _idem("nomfa")},
        json={},
    )
    assert no_mfa.status_code == 403
    assert no_mfa.json()["code"] == "MFA_REQUIRED"

    authenticator.identity = checker
    invalid = client.post(
        f"/api/v1/pia-records/{pia['resource_id']}/revoke",
        headers={"Idempotency-Key": _idem("invalid")},
        json={},
    )
    assert invalid.status_code == 409
    assert invalid.json()["code"] == "INVALID_STATE_TRANSITION"


def test_signed_cursor_is_filter_bound_and_tamper_evident(api) -> None:
    client, _, _, _ = api
    created_ids = {_create(client, "legal-basis-evidence")["resource_id"] for _ in range(3)}
    first = client.get("/api/v1/legal-basis-evidence?limit=2")
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    serialized_null = client.get("/api/v1/legal-basis-evidence", params={"state": "null"})
    assert serialized_null.status_code == 200
    assert {item["resource_id"] for item in serialized_null.json()["items"]} == (created_ids)

    second = client.get(
        "/api/v1/legal-basis-evidence",
        params={"limit": 2, "cursor": first_body["next_cursor"]},
    )
    assert second.status_code == 200
    returned_ids = {item["resource_id"] for item in first_body["items"] + second.json()["items"]}
    assert returned_ids == created_ids

    cursor = first_body["next_cursor"]
    tampered = f"{cursor[:-1]}{'A' if cursor[-1] != 'A' else 'B'}"
    bad_signature = client.get("/api/v1/legal-basis-evidence", params={"cursor": tampered})
    changed_filter = client.get(
        "/api/v1/legal-basis-evidence",
        params={"cursor": cursor, "state": "CURRENT"},
    )
    assert bad_signature.status_code == changed_filter.status_code == 400
    assert bad_signature.json()["code"] == "INVALID_CURSOR"
    assert changed_filter.json()["code"] == "INVALID_CURSOR"
