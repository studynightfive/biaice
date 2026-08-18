"""Application services for member-7 FR-09b risk acceptance."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.modules.approvals_reports.application.repository import (
    InMemoryApprovalsReportsRepository,
)
from biaice.modules.approvals_reports.domain.models import (
    RiskAcceptance,
    RiskAcceptanceState,
    RiskAcceptanceValidity,
    effective_risk_acceptance,
)


def _emit_event(
    outbox_port: OutboxPort | None,
    *,
    identity: IdentityContext,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: Mapping[str, Any],
    request_id: str,
) -> None:
    if outbox_port is None:
        return
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=(next(iter(identity.scope.project_ids)) if identity.scope.project_ids else None),
        decision_unit_id=(
            next(iter(identity.scope.decision_unit_ids))
            if identity.scope.decision_unit_ids
            else None
        ),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        occurred_at=datetime.now(timezone.utc),
        actor_id=identity.subject_id,
        request_id=request_id,
        correlation_id=uuid4(),
        causation_id=None,
        payload=dict(payload),
    )
    outbox_port.append(scope=identity.scope, event=envelope)


class RiskAcceptanceService:
    """Single writer for RiskAcceptanceVersion (FR-09b, MVP-B slice)."""

    def __init__(
        self,
        *,
        repository: InMemoryApprovalsReportsRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        risk: str,
        metric: str,
        acceptance_scope: str,
        rationale: str,
        independent_approver_id: UUID,
        valid_from: datetime,
        valid_until: datetime,
        request_id: str,
    ) -> RiskAcceptance:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        if identity.subject_id == independent_approver_id:
            raise BiaiceError(
                "MAKER_CHECKER_REQUIRED",
                detail=(
                    "The maker cannot also be the independent approver; choose a different checker."
                ),
            )
        if valid_until <= valid_from:
            raise BiaiceError(
                "RISK_ACCEPTANCE_INVALID_PERIOD",
                detail="valid_until must be later than valid_from.",
            )
        now = self.clock.now()
        item = RiskAcceptance(
            risk_acceptance_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=(
                next(iter(identity.scope.project_ids)) if identity.scope.project_ids else None
            ),
            decision_unit_id=decision_unit_id,
            state=RiskAcceptanceState.ACTIVE,
            validity=RiskAcceptanceValidity.CURRENT,
            risk=risk,
            metric=metric,
            acceptance_scope=acceptance_scope,
            rationale=rationale,
            independent_approver_id=independent_approver_id,
            valid_from=valid_from,
            valid_until=valid_until,
            created_at=now,
            created_by=identity.subject_id,
            accepted_at=now,
            accepted_by=independent_approver_id,
        )
        self.repository.upsert_risk_acceptance(item)
        self.audit_writer.write(
            identity=identity,
            action="approvals_reports.risk_acceptance.create",
            object_type="RiskAcceptance",
            object_id=item.risk_acceptance_id,
            request_id=request_id,
            reason_code="RISK_ACCEPTED",
            outcome=item.state.value,
            object_version_id=item.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="approvals_reports.risk_accepted.v1",
            aggregate_type="RiskAcceptance",
            aggregate_id=item.risk_acceptance_id,
            payload={
                "risk_acceptance_id": str(item.risk_acceptance_id),
                "version_id": str(item.version_id),
                "decision_unit_id": str(decision_unit_id),
                "state": item.state.value,
                "validity": item.validity.value,
                "valid_from": item.valid_from.isoformat(),
                "valid_until": item.valid_until.isoformat(),
            },
            request_id=request_id,
        )
        return item

    def list(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[RiskAcceptance, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        now = self.clock.now()
        return tuple(
            effective_risk_acceptance(item, now=now)
            for item in self.repository.list_risk_acceptances(
                scope=identity.scope, decision_unit_id=decision_unit_id
            )
        )

    def get(self, *, identity: IdentityContext, risk_acceptance_id: UUID) -> RiskAcceptance:
        item = self.repository.get_risk_acceptance(
            scope=identity.scope, risk_acceptance_id=risk_acceptance_id
        )
        if item is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"RiskAcceptance {risk_acceptance_id} not found in scope."),
            )
        return effective_risk_acceptance(item, now=self.clock.now())

    def revoke(
        self,
        *,
        identity: IdentityContext,
        risk_acceptance_id: UUID,
        revocation_reason: str,
        request_id: str,
    ) -> RiskAcceptance:
        require_audit(self.audit_writer)
        item = self.repository.get_risk_acceptance(
            scope=identity.scope, risk_acceptance_id=risk_acceptance_id
        )
        if item is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=(f"RiskAcceptance {risk_acceptance_id} not found in scope."),
            )
        effective = effective_risk_acceptance(item, now=self.clock.now())
        if effective.state is RiskAcceptanceState.REVOKED:
            raise BiaiceError(
                "RISK_ACCEPTANCE_ALREADY_REVOKED",
                detail="The risk acceptance is already revoked.",
            )
        if effective.state is RiskAcceptanceState.EXPIRED:
            raise BiaiceError(
                "RISK_ACCEPTANCE_EXPIRED",
                detail="The risk acceptance expired before revocation.",
            )
        now = self.clock.now()
        revoked = item.model_copy(
            update={
                "state": RiskAcceptanceState.REVOKED,
                "validity": RiskAcceptanceValidity.INVALIDATED,
                "revoked_at": now,
                "revoked_by": identity.subject_id,
                "revocation_reason": revocation_reason,
            }
        )
        self.repository.upsert_risk_acceptance(revoked)
        self.audit_writer.write(
            identity=identity,
            action="approvals_reports.risk_acceptance.revoke",
            object_type="RiskAcceptance",
            object_id=revoked.risk_acceptance_id,
            request_id=request_id,
            reason_code="RISK_REVOKED",
            outcome=revoked.state.value,
            object_version_id=revoked.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="approvals_reports.risk_revoked.v1",
            aggregate_type="RiskAcceptance",
            aggregate_id=revoked.risk_acceptance_id,
            payload={
                "risk_acceptance_id": str(revoked.risk_acceptance_id),
                "version_id": str(revoked.version_id),
                "decision_unit_id": str(revoked.decision_unit_id),
                "state": revoked.state.value,
                "validity": revoked.validity.value,
                "revoked_by": str(revoked.revoked_by),
                "revocation_reason": revoked.revocation_reason,
            },
            request_id=request_id,
        )
        return revoked


class ApprovalsReportsServices:
    """Composition root for the member-7 approvals/reports slice."""

    def __init__(
        self,
        *,
        repository: InMemoryApprovalsReportsRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.risk_acceptance = RiskAcceptanceService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )


def configure_approvals_reports(
    app, *, repository: InMemoryApprovalsReportsRepository | None = None
) -> ApprovalsReportsServices:
    """Attach member-7 services to the FastAPI app state."""
    repository = repository or InMemoryApprovalsReportsRepository()
    services = ApprovalsReportsServices(
        repository=repository,
        clock=SystemClock(),
        audit_writer=app.state.audit_writer,
        outbox_port=getattr(app.state, "outbox_port", None),
    )
    app.state.approvals_reports_repository = repository
    app.state.approvals_reports_services = services
    return services
