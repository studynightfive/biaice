"""Contract tests for member-4 FR-03/04 routers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from conftest import StaticAuthenticator
from fastapi import FastAPI
from fastapi.testclient import TestClient

from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.core.errors import install_error_handlers
from biaice.core.telemetry import RequestContextMiddleware
from biaice.main import create_app
from biaice.modules.commercial.api import router as commercial_router
from biaice.modules.commercial.application.services import configure_commercial
from biaice.modules.evidence.api import router as evidence_router
from biaice.modules.evidence.application.services import configure_evidence

NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
TENANT = uuid4()
DOMAIN = uuid4()
UNIT = uuid4()
ACTOR = uuid4()
CHECKER = uuid4()


def _identity(*, actor=ACTOR):
    return IdentityContext(
        subject_id=actor,
        username="m4-contract",
        roles=frozenset(
            {
                Role.DOCUMENT_SPECIALIST,
                Role.DOCUMENT_STEWARD,
                Role.FINANCE_AUTHOR,
                Role.FINANCE_APPROVER,
                Role.BID_MANAGER,
            }
        ),
        scope=TenantScope(
            tenant_id=TENANT,
            data_domain_id=DOMAIN,
            all_decision_units=True,
        ),
        mfa_verified=True,
        authenticated_at=NOW,
    )


def _platform_client(identity=None) -> TestClient:
    app = create_app(
        settings=Settings(environment="test"),
        authenticator=StaticAuthenticator(identity or _identity()),
    )
    return TestClient(app)


def _handler_client(identity=None) -> TestClient:
    """Mount member-4 routers without editing platform `main.py`."""
    platform = create_app(
        settings=Settings(environment="test"),
        authenticator=StaticAuthenticator(identity or _identity()),
    )
    app = FastAPI()
    app.state.settings = platform.state.settings
    app.state.authenticator = platform.state.authenticator
    app.state.audit_writer = platform.state.audit_writer
    app.state.document_read_port = getattr(platform.state, "document_read_port", None)
    configure_evidence(app)
    configure_commercial(app)
    install_error_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(evidence_router)
    app.include_router(commercial_router)
    return TestClient(app)


def _headers(idempotency: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer test-token-value",
        "Idempotency-Key": idempotency.ljust(16, "0"),
    }


def test_platform_app_keeps_member4_catalog_routes_as_501() -> None:
    client = _platform_client()
    empty = client.get(
        f"/api/v1/decision-units/{UNIT}/requirements",
        headers={"Authorization": "Bearer test-token-value"},
    )
    assert empty.status_code == 501
    assert empty.json()["code"] == "NOT_IMPLEMENTED"


def test_precheck_and_cost_routes_are_real_handlers_not_501() -> None:
    client = _handler_client()
    empty = client.get(
        f"/api/v1/decision-units/{UNIT}/requirements",
        headers={"Authorization": "Bearer test-token-value"},
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    created = client.post(
        f"/api/v1/decision-units/{UNIT}/precheck-assessments",
        headers=_headers("precheck-1"),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["decision"] == "UNKNOWN"
    assert "profit" not in body
    assert "market" not in body

    cost = client.post(
        f"/api/v1/decision-units/{UNIT}/cost-baselines",
        headers=_headers("cost-1"),
        json={
            "currency": "CNY",
            "tax_mode": "EXCLUSIVE",
            "input_vat": {"amount": "0.00", "currency": "CNY"},
            "cycle": "contract",
            "delivery_cost": {"amount": "10.00", "currency": "CNY"},
            "post_award_cost": {"amount": "1.00", "currency": "CNY"},
            "bid_preparation_cost": {"amount": "0.50", "currency": "CNY"},
            "cashflow_in": {"amount": "0.00", "currency": "CNY"},
            "cashflow_out": {"amount": "11.50", "currency": "CNY"},
        },
    )
    assert cost.status_code == 200
    assert cost.json()["exploration_only"] is True

    readiness = client.post(
        f"/api/v1/decision-units/{UNIT}/readiness-assessments",
        headers=_headers("ready-1"),
    )
    assert readiness.status_code == 200
    codes = {item["code"]: item for item in readiness.json()["items"]}
    assert codes["cost"]["commercial_not_procurement"] is True
    assert codes["precheck"]["commercial_not_procurement"] is False


def test_unauthenticated_evidence_list_is_401() -> None:
    client = _handler_client()
    response = client.get(f"/api/v1/decision-units/{UNIT}/evidence")
    assert response.status_code == 401


def test_condition_command_requires_reason_and_idempotency() -> None:
    client = _handler_client()
    created = client.post(
        f"/api/v1/decision-units/{UNIT}/conditions",
        headers=_headers("cond-1"),
        json={
            "title": "补证",
            "statement": "补充独立复核材料",
            "owner_id": str(ACTOR),
            "independent_reviewer_id": str(CHECKER),
            "due_at": (NOW + timedelta(days=3)).isoformat(),
            "blocking_stage": "APPROVAL",
        },
    )
    assert created.status_code == 200
    condition_id = created.json()["condition_id"]
    missing = client.post(
        f"/api/v1/conditions/{condition_id}/satisfy",
        headers={"Authorization": "Bearer test-token-value"},
        json={"reason": "done"},
    )
    assert missing.status_code == 400
    done = client.post(
        f"/api/v1/conditions/{condition_id}/satisfy",
        headers=_headers("cond-2"),
        json={"reason": "independent reviewer accepted the existing fact"},
    )
    assert done.status_code == 200
    assert done.json()["state"] == "SATISFIED"
