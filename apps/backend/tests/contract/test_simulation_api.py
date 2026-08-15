"""Contract tests for FR-06/07/08/09a simulation API."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from conftest import DOMAIN_A, StaticAuthenticator, TENANT_A
from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.main import create_app


def _identity():
    return IdentityContext(
        subject_id=uuid4(),
        username="m6",
        display_name="Member Six",
        roles=frozenset({Role.SIMULATION_ANALYST, Role.BID_MANAGER}),
        scope=TenantScope(
            tenant_id=TENANT_A,
            data_domain_id=DOMAIN_A,
            all_decision_units=True,
        ),
        mfa_verified=True,
        authenticated_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )


def _app():
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
    identity = _identity()
    audit = HashChainAuditWriter(InMemoryAppendOnlyAuditSink())
    app = create_app(
        settings=settings,
        authenticator=StaticAuthenticator(identity),
        audit_writer=audit,
    )
    return app


def _idem() -> str:
    return "idempotency-key-test-1234567890ab"


@pytest.fixture
def client():
    client = TestClient(_app())
    client.headers["Authorization"] = "Bearer test-token"
    return client


def _baseline_payload(unit):
    return {
        "decision_unit_id": str(unit),
        "manifest_items": [
            {
                "item_id": str(uuid4()),
                "upstream_type": "rules",
                "upstream_id": str(uuid4()),
                "upstream_version_id": str(uuid4()),
                "upstream_content_hash": "a" * 64,
                "dependency_type": "EVIDENTIAL",
                "recorded_at": "2026-08-15T00:00:00Z",
            }
        ],
    }


def test_list_decision_baselines_returns_empty(client):
    unit = uuid4()
    r = client.get("/api/v1/decision-units/" + str(unit) + "/decision-baselines")
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_freeze_decision_baseline_requires_idempotency(client):
    unit = uuid4()
    body = _baseline_payload(unit)
    r = client.post("/api/v1/decision-units/" + str(unit) + "/decision-baselines/freeze", json=body)
    assert r.status_code == 400
    assert r.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    r = client.post(
        "/api/v1/decision-units/" + str(unit) + "/decision-baselines/freeze",
        json=body,
        headers={"Idempotency-Key": _idem()},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["state"] == "FROZEN"
    assert payload["frozen_at"] is not None
    assert payload["frozen_by"] is not None
    assert payload["manifest"]["manifest_hash"]


def test_snapshot_enforces_shadow_watermark(client):
    unit = uuid4()
    r = client.post(
        "/api/v1/decision-units/" + str(unit) + "/simulation-assessment-snapshots",
        json={"payload": {"alpha": 1}},
        headers={"Idempotency-Key": _idem()},
    )
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["watermark"] == "SHADOW_PILOT_LOCKED"
    assert snap["state"] == "LOCKED"
    assert snap["payload_hash"]
    snapshot_id = snap["snapshot_id"]
    r = client.get("/api/v1/simulation-assessment-snapshots/" + snapshot_id + "/download")
    assert r.status_code == 200
    body = r.json()
    assert body["snapshot"]["watermark"] == "SHADOW_PILOT_LOCKED"
    r = client.get("/api/v1/decision-units/" + str(unit) + "/simulation-assessment-snapshots")
    assert r.status_code == 200
    assert any(item["snapshot_id"] == snapshot_id for item in r.json()["items"])
    r = client.get("/api/v1/simulation-assessment-snapshots/" + snapshot_id)
    assert r.status_code == 200


def test_recommendation_eligibility_blocks_unknown(client):
    unit = uuid4()
    body = _baseline_payload(unit)
    r = client.post(
        "/api/v1/decision-units/" + str(unit) + "/decision-baselines/freeze",
        json=body,
        headers={"Idempotency-Key": _idem()},
    )
    assert r.status_code == 200
    baseline_id = r.json()["baseline_id"]
    r = client.post(
        "/api/v1/decision-units/" + str(unit) + "/recommendation-eligibilities",
        json={
            "baseline_id": baseline_id,
            "snapshot_id": None,
            "precheck": "CURRENT",
            "readiness": "UNKNOWN",
            "static_validation": "CURRENT",
            "scenario_assessment": "CURRENT",
            "condition": "CURRENT",
            "risk_acceptance": "CURRENT",
        },
        headers={"Idempotency-Key": _idem()},
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "ELIGIBILITY_INPUT_UNKNOWN"


def test_openapi_marks_member_6_operations():
    settings = Settings(
        environment="test",
        deployment_profile="synthetic_http",
        audit_sink_required=False,
        audit_anchor_required=False,
        migrations_required=False,
        oidc_jwks_url=None,
        oidc_issuer=None,
    )
    app = create_app(
        settings=settings,
        authenticator=StaticAuthenticator(_identity()),
        audit_writer=HashChainAuditWriter(InMemoryAppendOnlyAuditSink()),
    )
    schema = app.openapi()
    owners = []
    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            if not isinstance(op, dict) or "operationId" not in op:
                continue
            owners.append((op["operationId"], op.get("x-owner")))
    m6 = [op for op in owners if op[1] == "member-6"]
    assert len(m6) >= 30, "expected at least 30 member-6 operations, got " + str(len(m6))
    sample = next(op for op in owners if op[1] == "member-2")
    assert sample[0]
