"""Unit tests for the member-7 RiskAcceptanceVersion service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.errors import BiaiceError
from biaice.modules.approvals_reports.application.repository import (
    InMemoryApprovalsReportsRepository,
)
from biaice.modules.approvals_reports.application.services import (
    RiskAcceptanceService,
)
from biaice.modules.approvals_reports.domain.models import (
    RiskAcceptanceState,
    RiskAcceptanceValidity,
)

TENANT = uuid4()
DOMAIN = uuid4()
UNIT = uuid4()
ACTOR = uuid4()
APPROVER = uuid4()
NOW = datetime(2026, 8, 16, tzinfo=timezone.utc)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _identity(*, mfa: bool = True, tenant=TENANT, domain=DOMAIN):
    return IdentityContext(
        subject_id=ACTOR,
        username="m7",
        display_name="Member Seven",
        roles=frozenset({Role.REPORT_MANAGER}),
        scope=TenantScope(
            tenant_id=tenant,
            data_domain_id=domain,
            all_decision_units=True,
        ),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


def _service(
    now: datetime | None = None,
    repository: InMemoryApprovalsReportsRepository | None = None,
) -> tuple[
    RiskAcceptanceService,
    HashChainAuditWriter,
    InMemoryAppendOnlyAuditSink,
    InMemoryApprovalsReportsRepository,
]:
    sink = InMemoryAppendOnlyAuditSink()
    audit = HashChainAuditWriter(sink, clock=FixedClock(now or NOW))
    repository = repository or InMemoryApprovalsReportsRepository()
    service = RiskAcceptanceService(
        repository=repository,
        clock=FixedClock(now or NOW),
        audit_writer=audit,
        outbox_port=None,
    )
    return service, audit, sink, repository


def _create_payload(service: RiskAcceptanceService, *, unit: object = UNIT, approver: object = APPROVER):
    return service.create(
        identity=_identity(),
        decision_unit_id=unit,
        risk="review risk",
        metric="scenario cv ar",
        acceptance_scope="unit bid under review",
        rationale="accepted by independent approver",
        independent_approver_id=approver,
        valid_from=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=30),
        request_id="req-1",
    )


def test_create_risk_acceptance_is_active_and_current() -> None:
    service, _, sink, _ = _service()

    item = _create_payload(service)

    assert item.state is RiskAcceptanceState.ACTIVE
    assert item.validity is RiskAcceptanceValidity.CURRENT
    assert item.created_by == ACTOR
    assert item.accepted_by == APPROVER
    actions = [event.action for event in sink.list_events(_identity().scope)]
    assert "approvals_reports.risk_acceptance.create" in actions
    listed = service.list(identity=_identity(), decision_unit_id=UNIT)
    assert [listed_item.risk_acceptance_id for listed_item in listed] == [
        item.risk_acceptance_id
    ]


def test_create_rejects_maker_checker_same_person() -> None:
    service, _, _, _ = _service()

    with pytest.raises(BiaiceError) as error:
        _create_payload(service, approver=ACTOR)

    assert error.value.code == "MAKER_CHECKER_REQUIRED"


def test_create_rejects_invalid_validity_period() -> None:
    service, _, _, _ = _service()

    with pytest.raises(BiaiceError) as error:
        service.create(
            identity=_identity(),
            decision_unit_id=UNIT,
            risk="review risk",
            metric="scenario cv ar",
            acceptance_scope="unit bid",
            rationale="accepted",
            independent_approver_id=APPROVER,
            valid_from=NOW,
            valid_until=NOW,
            request_id="req-1",
        )

    assert error.value.code == "RISK_ACCEPTANCE_INVALID_PERIOD"


def test_get_projects_expiry_without_mutating_history() -> None:
    service, _, _, repository = _service()
    item = _create_payload(service)
    later, _, _, _ = _service(now=NOW + timedelta(days=31), repository=repository)

    expired = later.get(identity=_identity(), risk_acceptance_id=item.risk_acceptance_id)
    assert expired.state is RiskAcceptanceState.EXPIRED
    assert expired.validity is RiskAcceptanceValidity.EXPIRED


def test_revoke_is_append_only_and_idempotent_fail_closed() -> None:
    service, _, sink, _ = _service()
    item = _create_payload(service)

    revoked = service.revoke(
        identity=_identity(),
        risk_acceptance_id=item.risk_acceptance_id,
        revocation_reason="upstream baseline changed",
        request_id="req-2",
    )

    assert revoked.state is RiskAcceptanceState.REVOKED
    assert revoked.validity is RiskAcceptanceValidity.INVALIDATED
    assert revoked.revoked_by == ACTOR
    with pytest.raises(BiaiceError) as error:
        service.revoke(
            identity=_identity(),
            risk_acceptance_id=item.risk_acceptance_id,
            revocation_reason="again",
            request_id="req-3",
        )
    assert error.value.code == "RISK_ACCEPTANCE_ALREADY_REVOKED"
    actions = [event.action for event in sink.list_events(_identity().scope)]
    assert "approvals_reports.risk_acceptance.revoke" in actions


def test_revoke_expired_risk_acceptance_is_blocked() -> None:
    service, _, _, repository = _service()
    item = _create_payload(service)
    later, _, _, _ = _service(now=NOW + timedelta(days=31), repository=repository)

    with pytest.raises(BiaiceError) as error:
        later.revoke(
            identity=_identity(),
            risk_acceptance_id=item.risk_acceptance_id,
            revocation_reason="late",
            request_id="req-4",
        )

    assert error.value.code == "RISK_ACCEPTANCE_EXPIRED"


def test_scope_isolation_hides_other_tenants() -> None:
    service, _, _, _ = _service()
    item = _create_payload(service)

    other_identity = _identity(tenant=uuid4())
    with pytest.raises(BiaiceError) as error:
        service.get(
            identity=other_identity,
            risk_acceptance_id=item.risk_acceptance_id,
        )
    assert error.value.code == "RESOURCE_NOT_FOUND"
