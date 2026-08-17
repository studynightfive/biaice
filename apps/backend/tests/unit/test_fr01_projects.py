"""Unit tests for member-2 DecisionUnit lifecycle writer and FR-01 services."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.errors import BiaiceError, install_error_handlers
from biaice.core.telemetry import RequestContextMiddleware
from biaice.modules.projects.application.repository import InMemoryFr01Repository
from biaice.modules.projects.application.services import configure_fr01
from biaice.modules.projects.domain.lifecycle import DecisionUnitLifecycleState, resolve_transition
from biaice.modules.projects.http import router as projects_router
from biaice.modules.rules.domain.models import RoundKind, ScopeSupport
from biaice.modules.rules.http import router as rules_router

TENANT = uuid4()
DOMAIN = uuid4()
ACTOR = uuid4()
PUBLISHER = uuid4()
NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class StaticAuthenticator:
    def __init__(self, identity: IdentityContext) -> None:
        self.identity = identity

    def authenticate(self, token: str) -> IdentityContext:
        assert token
        return self.identity


def _identity(
    *,
    roles: frozenset[Role] = frozenset({Role.BID_MANAGER}),
    subject_id=ACTOR,
    mfa: bool = True,
    all_projects: bool = True,
    all_units: bool = True,
) -> IdentityContext:
    return IdentityContext(
        subject_id=subject_id,
        username="m2",
        display_name="Member Two",
        roles=roles,
        scope=TenantScope(
            tenant_id=TENANT,
            data_domain_id=DOMAIN,
            all_projects=all_projects,
            all_decision_units=all_units,
        ),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


def _app(identity: IdentityContext | None = None) -> FastAPI:
    identity = identity or _identity()
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.state.authenticator = StaticAuthenticator(identity)
    app.state.audit_writer = HashChainAuditWriter(InMemoryAppendOnlyAuditSink(), clock=FixedClock())
    app.state.outbox_port = None
    configure_fr01(app, repository=InMemoryFr01Repository())
    app.state.projects_services.projects.clock = FixedClock()
    app.state.projects_services.units.clock = FixedClock()
    app.state.projects_services.lifecycle.clock = FixedClock()
    app.include_router(projects_router)
    app.include_router(rules_router)
    return app


def _client(identity: IdentityContext | None = None) -> TestClient:
    client = TestClient(_app(identity))
    client.headers["Authorization"] = "Bearer test-token"
    return client


def _idem() -> str:
    return "idempotency-key-m2-test-123456"


def test_reopened_is_event_not_state() -> None:
    nxt, reopened = resolve_transition(
        DecisionUnitLifecycleState.CANCELLED, "REOPENED"
    )
    assert reopened is True
    assert nxt is DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING


def test_illegal_transition_fails_closed() -> None:
    with pytest.raises(BiaiceError) as error:
        resolve_transition(DecisionUnitLifecycleState.DRAFT, "AWARDED")
    assert error.value.code == "REQUEST_VALIDATION_FAILED"


def test_system_admin_cannot_list_projects() -> None:
    client = _client(_identity(roles=frozenset({Role.SYSTEM_ADMIN})))
    response = client.get("/api/v1/projects")
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


def test_create_project_and_unit_then_list() -> None:
    client = _client()
    created = client.post(
        "/api/v1/projects",
        json={
            "name": "综合评分法合成项目",
            "purchaser_name": "合成采购人",
            "timezone": "Asia/Shanghai",
        },
        headers={"Idempotency-Key": _idem()},
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["project_id"]
    listed = client.get("/api/v1/projects")
    assert [item["project_id"] for item in listed.json()["items"]] == [project_id]

    unit = client.post(
        f"/api/v1/projects/{project_id}/decision-units",
        json={"name": "标段 A", "timezone": "Asia/Shanghai"},
        headers={"Idempotency-Key": _idem() + "u"},
    )
    assert unit.status_code == 200, unit.text
    assert unit.json()["lifecycle_state"] == "DRAFT"
    assert unit.json()["gap_summary"].startswith("范围、制度与规则尚未发布")


def test_lifecycle_append_only_and_cancel() -> None:
    client = _client()
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "生命周期", "purchaser_name": "合成采购人", "timezone": "UTC"},
        headers={"Idempotency-Key": _idem()},
    ).json()["project_id"]
    unit_id = client.post(
        f"/api/v1/projects/{project_id}/decision-units",
        json={"name": "单元", "timezone": "UTC"},
        headers={"Idempotency-Key": _idem() + "u"},
    ).json()["decision_unit_id"]

    first = client.post(
        f"/api/v1/decision-units/{unit_id}/transition-commands",
        json={"command": "REGIME_AND_SCOPE_PENDING", "reason": "开始范围确认"},
        headers={"Idempotency-Key": _idem() + "t1"},
    )
    assert first.status_code == 200, first.text
    cancelled = client.post(
        f"/api/v1/decision-units/{unit_id}/transition-commands",
        json={"command": "CANCELLED", "reason": "采购取消"},
        headers={"Idempotency-Key": _idem() + "t2"},
    )
    assert cancelled.status_code == 200
    reopened = client.post(
        f"/api/v1/decision-units/{unit_id}/transition-commands",
        json={
            "command": "REOPENED",
            "reason": "补遗恢复",
            "basis": "addendum-1",
            "earliest_affected_stage": "REGIME_AND_SCOPE_PENDING",
        },
        headers={"Idempotency-Key": _idem() + "t3"},
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["reopened"] is True
    assert reopened.json()["from_state"] == "CANCELLED"
    events = client.get(f"/api/v1/decision-units/{unit_id}/lifecycle-events").json()["items"]
    assert [item["sequence"] for item in events] == [1, 2, 3]


def test_scope_publish_requires_independent_publisher_and_blocks_multi_round() -> None:
    maker = _client(_identity(subject_id=ACTOR))
    project_id = maker.post(
        "/api/v1/projects",
        json={"name": "多轮阻断", "purchaser_name": "合成采购人", "timezone": "Asia/Shanghai"},
        headers={"Idempotency-Key": _idem()},
    ).json()["project_id"]
    unit_id = maker.post(
        f"/api/v1/projects/{project_id}/decision-units",
        json={"name": "谈判标段", "timezone": "Asia/Shanghai"},
        headers={"Idempotency-Key": _idem() + "u"},
    ).json()["decision_unit_id"]
    draft = maker.post(
        f"/api/v1/decision-units/{unit_id}/scope-assessments",
        json={
            "support": ScopeSupport.MULTI_ROUND_UNSUPPORTED.value,
            "round_kind": RoundKind.MULTI_ROUND.value,
            "cross_lot": False,
            "reason_codes": ["MULTI_ROUND"],
        },
        headers={"Idempotency-Key": _idem() + "s"},
    )
    assert draft.status_code == 200, draft.text
    same_person = maker.post(
        f"/api/v1/scope-assessments/{draft.json()['scope_assessment_id']}/publish",
        headers={"Idempotency-Key": _idem() + "p0"},
    )
    assert same_person.status_code == 409
    assert same_person.json()["code"] == "MAKER_CHECKER_REQUIRED"

    publisher = _client(_identity(subject_id=PUBLISHER))
    # Publisher uses a new in-memory store unless we share repository. Isolated apps
    # do not share state, so publish against the maker app with a swapped identity.
    app = maker.app
    app.state.authenticator = StaticAuthenticator(_identity(subject_id=PUBLISHER))
    published = TestClient(app)
    published.headers["Authorization"] = "Bearer test-token"
    ok = published.post(
        f"/api/v1/scope-assessments/{draft.json()['scope_assessment_id']}/publish",
        headers={"Idempotency-Key": _idem() + "p1"},
    )
    assert ok.status_code == 200, ok.text
    unit = published.get(f"/api/v1/decision-units/{unit_id}").json()
    assert unit["lifecycle_state"] == "MULTI_ROUND_UNSUPPORTED"


def test_rule_conflict_does_not_use_last_write_wins() -> None:
    client = _client()
    project_id = client.post(
        "/api/v1/projects",
        json={"name": "规则冲突", "purchaser_name": "合成采购人", "timezone": "Asia/Shanghai"},
        headers={"Idempotency-Key": _idem()},
    ).json()["project_id"]
    unit_id = client.post(
        f"/api/v1/projects/{project_id}/decision-units",
        json={"name": "单元", "timezone": "Asia/Shanghai"},
        headers={"Idempotency-Key": _idem() + "u"},
    ).json()["decision_unit_id"]
    rule_set = client.post(
        f"/api/v1/decision-units/{unit_id}/rule-sets",
        json={"title": "冲突集"},
        headers={"Idempotency-Key": _idem() + "rs"},
    ).json()
    client.post(
        f"/api/v1/rule-sets/{rule_set['rule_set_id']}/clauses",
        json={
            "kind": "ROUNDING",
            "coverage_key": "price.rounding",
            "priority": 10,
            "original_text": "四舍五入到元",
            "structured_expression": "round=1",
            "confidence": 0.9,
        },
        headers={"Idempotency-Key": _idem() + "c1"},
    )
    client.post(
        f"/api/v1/rule-sets/{rule_set['rule_set_id']}/clauses",
        json={
            "kind": "ROUNDING",
            "coverage_key": "price.rounding",
            "priority": 20,
            "original_text": "向下截断到分",
            "structured_expression": "trunc=0.01",
            "confidence": 0.8,
        },
        headers={"Idempotency-Key": _idem() + "c2"},
    )
    resolutions = client.app.state.rules_services.clauses.resolve_unit(
        identity=_identity(), unit_id=UUID(unit_id), formal=False
    )
    assert resolutions[0].status.value == "CONFLICT_REQUIRES_CONFIRMATION"
    assert resolutions[0].winning_clause_id is None


def test_empty_lists_and_unauthorized_unit_look_missing() -> None:
    client = _client()
    missing = client.get(f"/api/v1/decision-units/{uuid4()}")
    assert missing.status_code == 404
    scoped = _client(_identity(all_units=False, all_projects=False))
    empty = scoped.get("/api/v1/projects")
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["has_more"] is False
