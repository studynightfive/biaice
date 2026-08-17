"""FR-01 gold fixtures, inheritance, SQL adapter, pagination and document events."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.db import Base
from biaice.core.errors import install_error_handlers
from biaice.core.http import CursorCodec
from biaice.core.outbox import EventEnvelope
from biaice.core.telemetry import RequestContextMiddleware
from biaice.modules.projects.application.document_events import DocumentEventConsumer
from biaice.modules.projects.application.repository import InMemoryFr01Repository
from biaice.modules.projects.application.services import configure_fr01
from biaice.modules.projects.domain.gold import apply_formula, apply_rounding, apply_tie
from biaice.modules.projects.domain.models import ResourceValidity
from biaice.modules.projects.fixtures import (
    FORMULA_EXPR,
    ROUNDING_HALF_UP,
    TIE_EXPR,
    seed_gold_projects,
)
from biaice.modules.projects.http import router as projects_router
from biaice.modules.projects.infrastructure.models import (
    ApplicableRegimeRow,
    ComplianceReviewRow,
    CrossLotConstraintRow,
    DecisionUnitLifecycleEventRow,
    DecisionUnitRow,
    DocumentIntakeRefRow,
    ProcurementProjectRow,
    RuleClauseRow,
    RuleSetRow,
    ScopeAssessmentRow,
)
from biaice.modules.projects.infrastructure.sql_repository import SqlAlchemyFr01Repository
from biaice.modules.rules.domain.models import ResolutionStatus
from biaice.modules.rules.http import router as rules_router

TENANT = uuid4()
DOMAIN = uuid4()
ACTOR = uuid4()
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


def _identity() -> IdentityContext:
    return IdentityContext(
        subject_id=ACTOR,
        username="m2",
        display_name="Member Two",
        roles=frozenset({Role.BID_MANAGER}),
        scope=TenantScope(
            tenant_id=TENANT,
            data_domain_id=DOMAIN,
            all_projects=True,
            all_decision_units=True,
        ),
        mfa_verified=True,
        authenticated_at=NOW,
    )


def _app(repository=None, *, codec: CursorCodec | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.state.authenticator = StaticAuthenticator(_identity())
    app.state.audit_writer = HashChainAuditWriter(
        InMemoryAppendOnlyAuditSink(), clock=FixedClock()
    )
    app.state.outbox_port = None
    if codec is not None:
        app.state.cursor_codec = codec
    configure_fr01(app, repository=repository or InMemoryFr01Repository())
    app.state.projects_services.projects.clock = FixedClock()
    app.state.projects_services.units.clock = FixedClock()
    app.state.projects_services.lifecycle.clock = FixedClock()
    app.state.rules_services.clauses.clock = FixedClock()
    app.include_router(projects_router)
    app.include_router(rules_router)
    return app


def test_gold_formula_rounding_and_tie_are_100_percent() -> None:
    score = apply_formula(
        FORMULA_EXPR,
        {"tech": Decimal("90"), "price": Decimal("80")},
    )
    assert score == Decimal("84.0")
    assert apply_rounding(ROUNDING_HALF_UP, Decimal("84.005")) == Decimal("84.01")
    assert apply_rounding(ROUNDING_HALF_UP, Decimal("1.225")) == Decimal("1.23")
    ranked = apply_tie(
        TIE_EXPR,
        (
            {
                "id": "b",
                "score": Decimal("84.00"),
                "price": Decimal("101"),
                "bid_time": "10:00",
            },
            {
                "id": "a",
                "score": Decimal("84.00"),
                "price": Decimal("100"),
                "bid_time": "10:05",
            },
            {
                "id": "c",
                "score": Decimal("83.00"),
                "price": Decimal("90"),
                "bid_time": "09:00",
            },
        ),
    )
    assert [row["id"] for row in ranked] == ["a", "b", "c"]


def test_three_synthetic_projects_resolve_as_specified() -> None:
    repository = InMemoryFr01Repository()
    identity = _identity()
    gold = seed_gold_projects(repository, scope=identity.scope, actor_id=identity.subject_id)
    app = _app(repository)
    clauses = app.state.rules_services.clauses

    scoring = clauses.resolve_unit(
        identity=identity,
        unit_id=gold["comprehensive_scoring"].unit.decision_unit_id,
        formal=True,
    )
    by_key = {item.coverage_key: item for item in scoring}
    assert by_key["score.formula"].status is ResolutionStatus.RESOLVED
    assert by_key["price.rounding"].status is ResolutionStatus.RESOLVED
    assert by_key["score.tie"].status is ResolutionStatus.RESOLVED
    assert "Unit override matches inherited project clause." in by_key["price.rounding"].detail

    lowest = clauses.resolve_unit(
        identity=identity,
        unit_id=gold["lowest_evaluated_price"].unit.decision_unit_id,
        formal=True,
    )
    assert {item.coverage_key for item in lowest} == {
        "substantive.delivery",
        "price.abnormally_low",
        "supplier.valid_count",
    }
    assert all(item.status is ResolutionStatus.RESOLVED for item in lowest)

    conflicted = clauses.resolve_unit(
        identity=identity,
        unit_id=gold["conflict_and_blocks"].unit.decision_unit_id,
        formal=True,
    )
    rounding = next(item for item in conflicted if item.coverage_key == "price.rounding")
    assert rounding.status is ResolutionStatus.CONFLICT_REQUIRES_CONFIRMATION
    assert rounding.winning_clause_id is None
    assert not any(item.coverage_key == "score.tie" for item in conflicted)


def test_sqlalchemy_repository_round_trips_a_project() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            ProcurementProjectRow.__table__,
            DecisionUnitRow.__table__,
            DecisionUnitLifecycleEventRow.__table__,
            ScopeAssessmentRow.__table__,
            ApplicableRegimeRow.__table__,
            RuleSetRow.__table__,
            RuleClauseRow.__table__,
            ComplianceReviewRow.__table__,
            CrossLotConstraintRow.__table__,
            DocumentIntakeRefRow.__table__,
        ],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    repository = SqlAlchemyFr01Repository(factory)
    identity = _identity()
    gold = seed_gold_projects(repository, scope=identity.scope, actor_id=identity.subject_id)
    loaded = repository.get_project(
        scope=identity.scope,
        project_id=gold["comprehensive_scoring"].project.project_id,
    )
    assert loaded is not None
    assert loaded.name == "综合评分法合成项目"
    units = repository.list_units(
        scope=identity.scope,
        project_id=gold["comprehensive_scoring"].project.project_id,
    )
    assert len(units) == 1


def test_document_event_consumer_is_idempotent_and_quarantine_unusable() -> None:
    repository = InMemoryFr01Repository()
    consumer = DocumentEventConsumer(repository)
    identity = _identity()
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type="documents.source_document_released.v1",
        schema_version=1,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=uuid4(),
        decision_unit_id=uuid4(),
        aggregate_type="SourceDocument",
        aggregate_id=uuid4(),
        occurred_at=NOW,
        actor_id=identity.subject_id,
        request_id="req-doc-1",
        correlation_id=uuid4(),
        causation_id=None,
        payload={"document_id": str(uuid4()), "status": "RELEASED"},
    )
    first = consumer.consume(envelope)
    second = consumer.consume(envelope)
    assert first is not None and second is not None
    assert first.event_id == second.event_id
    assert first.usable_for_formal_rules is True
    assert len(repository.list_document_refs(scope=identity.scope)) == 1

    quarantined = consumer.consume(
        envelope.model_copy(
            update={
                "event_id": uuid4(),
                "event_type": "documents.document_quarantined.v1",
                "request_id": "req-doc-2",
                "correlation_id": uuid4(),
            }
        )
    )
    assert quarantined is not None
    assert quarantined.usable_for_formal_rules is False
    assert quarantined.validity_state is ResourceValidity.INVALIDATED
    assert (
        consumer.consume(
            envelope.model_copy(
                update={
                    "event_id": uuid4(),
                    "event_type": "evidence.published.v1",
                    "request_id": "req-other",
                    "correlation_id": uuid4(),
                    "aggregate_type": "Evidence",
                }
            )
        )
        is None
    )


def test_list_projects_uses_signed_cursor() -> None:
    codec = CursorCodec(b"x" * 32)
    client = TestClient(_app(codec=codec))
    client.headers["Authorization"] = "Bearer test-token"
    for index in range(3):
        created = client.post(
            "/api/v1/projects",
            json={
                "name": f"分页项目 {index}",
                "purchaser_name": "合成采购人",
                "timezone": "Asia/Shanghai",
            },
            headers={"Idempotency-Key": f"idempotency-key-m2-page-{index:02d}-xxxx"},
        )
        assert created.status_code == 200, created.text
    first = client.get("/api/v1/projects", params={"limit": 2})
    assert first.status_code == 200
    body = first.json()
    assert len(body["items"]) == 2
    assert body["has_more"] is True
    assert body["next_cursor"]
    second = client.get(
        "/api/v1/projects", params={"limit": 2, "cursor": body["next_cursor"]}
    )
    assert second.status_code == 200
    assert len(second.json()["items"]) == 1
    assert second.json()["has_more"] is False
