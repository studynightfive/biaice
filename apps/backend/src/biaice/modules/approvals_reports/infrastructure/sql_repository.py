"""SQLAlchemy adapter for the member-7 RiskAcceptanceVersion slice."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from biaice.core.auth import TenantScope
from biaice.core.db import tenant_transaction
from biaice.modules.approvals_reports.application.repository import _scope_matches
from biaice.modules.approvals_reports.domain.models import (
    RiskAcceptance,
    RiskAcceptanceState,
    RiskAcceptanceValidity,
)
from biaice.modules.approvals_reports.infrastructure.models import RiskAcceptanceRow


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _write_scope(item: RiskAcceptance) -> TenantScope:
    return TenantScope(
        tenant_id=item.tenant_id,
        data_domain_id=item.data_domain_id,
        project_ids=frozenset({item.project_id}) if item.project_id is not None else frozenset(),
        decision_unit_ids=frozenset({item.decision_unit_id}),
    )


def _row_to_model(row: RiskAcceptanceRow) -> RiskAcceptance:
    return RiskAcceptance(
        risk_acceptance_id=row.risk_acceptance_id,
        version_id=row.version_id,
        tenant_id=row.tenant_id,
        data_domain_id=row.data_domain_id,
        project_id=row.project_id,
        decision_unit_id=row.decision_unit_id,
        state=RiskAcceptanceState(row.state),
        validity=RiskAcceptanceValidity(row.validity),
        risk=row.risk,
        metric=row.metric,
        acceptance_scope=row.acceptance_scope,
        rationale=row.rationale,
        independent_approver_id=row.independent_approver_id,
        valid_from=_utc(row.valid_from),
        valid_until=_utc(row.valid_until),
        created_at=_utc(row.created_at),
        created_by=row.created_by,
        accepted_at=_utc(row.accepted_at),
        accepted_by=row.accepted_by,
        revoked_at=None if row.revoked_at is None else _utc(row.revoked_at),
        revoked_by=row.revoked_by,
        revocation_reason=row.revocation_reason,
    )


def _apply_model(row: RiskAcceptanceRow, item: RiskAcceptance) -> None:
    row.tenant_id = item.tenant_id
    row.data_domain_id = item.data_domain_id
    row.project_id = item.project_id
    row.decision_unit_id = item.decision_unit_id
    row.version_id = item.version_id
    row.state = item.state.value
    row.validity = item.validity.value
    row.risk = item.risk
    row.metric = item.metric
    row.acceptance_scope = item.acceptance_scope
    row.rationale = item.rationale
    row.independent_approver_id = item.independent_approver_id
    row.valid_from = item.valid_from
    row.valid_until = item.valid_until
    row.created_at = item.created_at
    row.created_by = item.created_by
    row.accepted_at = item.accepted_at
    row.accepted_by = item.accepted_by
    row.revoked_at = item.revoked_at
    row.revoked_by = item.revoked_by
    row.revocation_reason = item.revocation_reason


class SqlAlchemyApprovalsReportsRepository:
    """PostgreSQL (and sqlite-in-test) persistence for RiskAcceptanceVersion."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _tx(self, scope: TenantScope) -> Iterator[Session]:
        session = self._session_factory()
        try:
            with tenant_transaction(session, scope):
                yield session
                session.flush()
        finally:
            session.close()

    def upsert_risk_acceptance(self, item: RiskAcceptance) -> None:
        with self._tx(_write_scope(item)) as session:
            row = session.get(RiskAcceptanceRow, item.risk_acceptance_id)
            if row is None:
                row = RiskAcceptanceRow(risk_acceptance_id=item.risk_acceptance_id)
                session.add(row)
            _apply_model(row, item)

    def get_risk_acceptance(
        self, *, scope: TenantScope, risk_acceptance_id: UUID
    ) -> RiskAcceptance | None:
        with self._tx(scope) as session:
            row = session.get(RiskAcceptanceRow, risk_acceptance_id)
            if row is None:
                return None
            item = _row_to_model(row)
        if not _scope_matches(item, scope):
            return None
        return item

    def list_risk_acceptances(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[RiskAcceptance, ...]:
        with self._tx(scope) as session:
            rows = (
                session.query(RiskAcceptanceRow)
                .filter(RiskAcceptanceRow.decision_unit_id == decision_unit_id)
                .all()
            )
            items = [_row_to_model(row) for row in rows]
        selected = [item for item in items if _scope_matches(item, scope)]
        selected.sort(key=lambda item: (item.created_at, str(item.version_id)))
        return tuple(selected)
