"""Unit tests for member-4 FR-04 cost, policy and readiness."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.errors import BiaiceError
from biaice.core.money import Money
from biaice.modules.commercial.application.repository import InMemoryCommercialRepository
from biaice.modules.commercial.application.services import CommercialService
from biaice.modules.commercial.domain.models import ReadinessDecision, TaxMode
from biaice.modules.evidence.application.ports import EvidenceReadinessView
from biaice.modules.evidence.domain.models import PrecheckDecision, ValidityState

TENANT = uuid4()
DOMAIN = uuid4()
UNIT = uuid4()
AUTHOR = uuid4()
APPROVER = uuid4()
NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class StaticEvidencePort:
    def __init__(self, view: EvidenceReadinessView) -> None:
        self.view = view

    def current_view(self, *, scope, decision_unit_id):
        del scope, decision_unit_id
        return self.view


def _identity(*, actor=AUTHOR, tenant=TENANT):
    return IdentityContext(
        subject_id=actor,
        username="finance",
        roles=frozenset({Role.FINANCE_AUTHOR, Role.FINANCE_APPROVER}),
        scope=TenantScope(
            tenant_id=tenant,
            data_domain_id=DOMAIN,
            all_decision_units=True,
        ),
        mfa_verified=True,
        authenticated_at=NOW,
    )


def _cny(amount: str) -> Money:
    return Money(amount=Decimal(amount), currency="CNY")


def _service(evidence_view: EvidenceReadinessView | None = None):
    sink = InMemoryAppendOnlyAuditSink()
    audit = HashChainAuditWriter(sink, clock=FixedClock(NOW))
    view = evidence_view or EvidenceReadinessView(
        precheck_decision=PrecheckDecision.PASS,
        precheck_validity=ValidityState.CURRENT,
        response_profile_current=True,
        subject_qualification=None,
        unmapped_mandatory_count=0,
        open_blocking_condition_count=0,
    )
    service = CommercialService(
        repository=InMemoryCommercialRepository(),
        clock=FixedClock(NOW),
        audit_writer=audit,
        outbox_port=None,
        evidence_readiness_port=StaticEvidencePort(view),
        market_readiness_port=type(
            "NoMarket", (), {"current_view": staticmethod(lambda **kwargs: None)}
        )(),
    )
    return service, sink


def _create_cost(service: CommercialService, identity=None):
    return service.create_cost_baseline(
        identity=identity or _identity(),
        decision_unit_id=UNIT,
        currency="CNY",
        tax_mode=TaxMode.EXCLUSIVE,
        input_vat=_cny("0.00"),
        cycle="contract",
        delivery_cost=_cny("100000.00"),
        post_award_cost=_cny("8000.00"),
        bid_preparation_cost=_cny("1200.00"),
        cashflow_in=_cny("0.00"),
        cashflow_out=_cny("109200.00"),
        request_id="c1",
    )


def test_unapproved_cost_is_exploration_only_and_blocks_publish() -> None:
    service, _ = _service()
    cost = _create_cost(service)
    assert cost.exploration_only is True
    with pytest.raises(BiaiceError) as error:
        service.publish_cost_baseline(
            identity=_identity(actor=APPROVER),
            cost_baseline_id=cost.cost_baseline_id,
            request_id="c2",
        )
    assert error.value.code == "DOCUMENT_NOT_RELEASABLE"
    assert error.value.detail == "COST_NOT_APPROVED"


def test_cost_maker_cannot_approve() -> None:
    service, _ = _service()
    cost = _create_cost(service)
    with pytest.raises(BiaiceError) as error:
        service.approve_cost_baseline(
            identity=_identity(actor=AUTHOR),
            cost_baseline_id=cost.cost_baseline_id,
            request_id="c2",
        )
    assert error.value.code == "MAKER_CHECKER_REQUIRED"


def test_approved_cost_can_publish_and_readiness_keeps_commercial_separate() -> None:
    service, _ = _service()
    cost = _create_cost(service)
    approved = service.approve_cost_baseline(
        identity=_identity(actor=APPROVER),
        cost_baseline_id=cost.cost_baseline_id,
        request_id="c2",
    )
    published = service.publish_cost_baseline(
        identity=_identity(actor=APPROVER),
        cost_baseline_id=approved.cost_baseline_id,
        request_id="c3",
    )
    assert published.exploration_only is False
    policy = service.create_policy(
        identity=_identity(),
        decision_unit_id=UNIT,
        profit_floor="0.08",
        cashflow_constraint="non-negative operating cash",
        capacity_constraint="single lot",
        risk_threshold="no unaccepted review risk",
        coverage_ratio="0.80",
        min_award_quality="eligible_for_award",
        objective_weights={"rank": "0.5", "value": "0.5"},
        merge_tolerance="0.01",
        exception_authority="finance committee",
        request_id="p1",
    )
    service.publish_policy(
        identity=_identity(actor=APPROVER), policy_id=policy.policy_id, request_id="p2"
    )
    readiness = service.create_readiness(
        identity=_identity(), decision_unit_id=UNIT, request_id="r1"
    )
    by_code = {item.code: item for item in readiness.items}
    assert by_code["cost"].commercial_not_procurement is True
    assert by_code["policy"].commercial_not_procurement is True
    assert by_code["precheck"].commercial_not_procurement is False
    assert by_code["market"].decision is ReadinessDecision.UNKNOWN
    assert readiness.decision is not ReadinessDecision.READY
    assert readiness.exploration_watermark is True


def test_precheck_pass_does_not_flip_when_cost_is_missing() -> None:
    service, _ = _service(
        EvidenceReadinessView(
            precheck_decision=PrecheckDecision.PASS,
            precheck_validity=ValidityState.CURRENT,
            response_profile_current=True,
            subject_qualification=None,
            unmapped_mandatory_count=0,
            open_blocking_condition_count=0,
        )
    )
    readiness = service.create_readiness(
        identity=_identity(), decision_unit_id=UNIT, request_id="r1"
    )
    by_code = {item.code: item for item in readiness.items}
    assert by_code["precheck"].decision is ReadinessDecision.READY
    assert by_code["cost"].decision is ReadinessDecision.UNKNOWN
    assert by_code["cost"].reason_code == "COST_MISSING"


def test_binary_float_money_is_rejected() -> None:
    with pytest.raises(ValueError):
        Money(amount=1.2, currency="CNY")  # type: ignore[arg-type]
