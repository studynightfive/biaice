"""Approvals/reports repository ports and in-memory fallback."""

from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.approvals_reports.domain.models import RiskAcceptance


class ApprovalsReportsRepository(Protocol):
    def upsert_risk_acceptance(self, item: RiskAcceptance) -> None: ...

    def get_risk_acceptance(
        self, *, scope: TenantScope, risk_acceptance_id: UUID
    ) -> RiskAcceptance | None: ...

    def list_risk_acceptances(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[RiskAcceptance, ...]: ...


def _scope_matches(item: RiskAcceptance, scope: TenantScope) -> bool:
    if item.tenant_id != scope.tenant_id or item.data_domain_id != scope.data_domain_id:
        return False
    if (
        item.project_id is not None
        and not scope.all_projects
        and item.project_id not in scope.project_ids
    ):
        return False
    if not scope.all_decision_units and item.decision_unit_id not in scope.decision_unit_ids:
        return False
    return True


class InMemoryApprovalsReportsRepository:
    """Thread-safe in-memory store for tests and composition fallback.

    Production composition uses ``SqlAlchemyApprovalsReportsRepository`` when a
    session factory is available; both implement :class:`ApprovalsReportsRepository`.
    """

    def __init__(self) -> None:
        self._risk_acceptances: dict[UUID, RiskAcceptance] = {}
        self._lock = threading.Lock()

    def upsert_risk_acceptance(self, item: RiskAcceptance) -> None:
        with self._lock:
            self._risk_acceptances[item.risk_acceptance_id] = item

    def get_risk_acceptance(
        self, *, scope: TenantScope, risk_acceptance_id: UUID
    ) -> RiskAcceptance | None:
        with self._lock:
            item = self._risk_acceptances.get(risk_acceptance_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def list_risk_acceptances(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[RiskAcceptance, ...]:
        with self._lock:
            items = [
                item
                for item in self._risk_acceptances.values()
                if _scope_matches(item, scope) and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.version_id)))
        return tuple(items)
