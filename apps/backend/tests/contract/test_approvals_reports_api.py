"""Contract tests for the member-7 FR-09b risk acceptance API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from conftest import DOMAIN_A, TENANT_A, StaticAuthenticator
from fastapi.testclient import TestClient

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.main import create_app

NOW = datetime(2026, 8, 16, tzinfo=timezone.utc)


def _identity(
    *,
    roles: frozenset[Role] = frozenset({Role.REPORT_MANAGER}),
    mfa: bool = True,
    tenant=TENANT_A,
    domain=DOMAIN_A,
    all_decision_units: bool = True,
    decision_unit_ids: frozenset = frozenset(),
) -> IdentityContext:
    return IdentityContext(
        subject_id=uuid4(),
        username="m7",
        display_name="Member Seven",
        roles=roles,
        scope=TenantScope(
            tenant_id=tenant,
            data_domain_id=domain,
            all_decision_units=all_decision_units,
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
    app = create_app(
        settings=settings,
        authenticator=StaticAuthenticator(identity),
        audit_writer=HashChainAuditWriter(InMemoryAppendOnlyAuditSink()),
    )
    return app


@pytest.fixture
def client():
    client = TestClient(_app())
    client.headers["Authorization"] = "Bearer test-token"
    return client


def _idem() -> str:
    return "idempotency-key-test-1234567890ab"


def _create_body(approver=None):
    return {
        "risk": "review risk",
        "metric": "scenario cvar",
        "acceptance_scope": "unit bid under review",
        "rationale": "independent approver accepted",
        "independent_approver_id": str(approver or uuid4()),
        "valid_from": (NOW - timedelta(days=1)).isoformat(),
        "valid_until": (NOW + timedelta(days=30)).isoformat(),
    }


def test_list_risk_acceptances_returns_empty(client):
    unit = uuid4()
    response = client.get(f"/api/v1/decision-units/{unit}/risk-acceptances")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_create_risk_acceptance_requires_idempotency(client):
    unit = uuid4()
    response = client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_create_risk_acceptance_and_read_back(client):
    unit = uuid4()
    response = client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(),
        headers={"Idempotency-Key": _idem()},
    )
    assert response.status_code == 200, response.text
    item = response.json()
    assert item["state"] == "ACTIVE"
    assert item["validity"] == "CURRENT"
    assert item["decision_unit_id"] == str(unit)

    listed = client.get(f"/api/v1/decision-units/{unit}/risk-acceptances").json()
    assert [row["risk_acceptance_id"] for row in listed["items"]] == [
        item["risk_acceptance_id"]
    ]
    fetched = client.get(f"/api/v1/risk-acceptances/{item['risk_acceptance_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["version_id"] == item["version_id"]


def test_create_rejects_maker_checker_same_person(client):
    unit = uuid4()
    identity = _identity()
    client = TestClient(_app(identity))
    client.headers["Authorization"] = "Bearer test-token"
    response = client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(approver=identity.subject_id),
        headers={"Idempotency-Key": _idem()},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "MAKER_CHECKER_REQUIRED"


def test_revoke_requires_idempotency_and_is_append_only(client):
    unit = uuid4()
    item = client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(),
        headers={"Idempotency-Key": _idem()},
    ).json()

    missing = client.post(
        f"/api/v1/risk-acceptances/{item['risk_acceptance_id']}/revoke",
        json={"revocation_reason": "upstream changed"},
    )
    assert missing.status_code == 400
    assert missing.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    revoked = client.post(
        f"/api/v1/risk-acceptances/{item['risk_acceptance_id']}/revoke",
        json={"revocation_reason": "upstream changed"},
        headers={"Idempotency-Key": _idem()},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["state"] == "REVOKED"
    assert revoked.json()["validity"] == "INVALIDATED"

    again = client.post(
        f"/api/v1/risk-acceptances/{item['risk_acceptance_id']}/revoke",
        json={"revocation_reason": "again"},
        headers={"Idempotency-Key": _idem() + "x"},
    )
    assert again.status_code == 409
    assert again.json()["code"] == "RISK_ACCEPTANCE_ALREADY_REVOKED"


def test_create_requires_permission_and_mfa():
    unit = uuid4()
    client = TestClient(_app(_identity(roles=frozenset({Role.AUDITOR}))))
    client.headers["Authorization"] = "Bearer test-token"
    response = client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(),
        headers={"Idempotency-Key": _idem()},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"

    mfa_client = TestClient(_app(_identity(mfa=False)))
    mfa_client.headers["Authorization"] = "Bearer test-token"
    response = mfa_client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(),
        headers={"Idempotency-Key": _idem()},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "MFA_REQUIRED"


def test_scope_violation_looks_like_missing_resource():
    allowed_unit = uuid4()
    unit = uuid4()

    client = TestClient(
        _app(
            _identity(
                all_decision_units=False,
                decision_unit_ids=frozenset({allowed_unit}),
            )
        )
    )
    client.headers["Authorization"] = "Bearer test-token"
    response = client.post(
        f"/api/v1/decision-units/{unit}/risk-acceptances",
        json=_create_body(),
        headers={"Idempotency-Key": _idem()},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "TENANT_SCOPE_VIOLATION"
