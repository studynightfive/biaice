"""In-memory FR-04 repository."""

from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.commercial.domain.models import (
    CommercialPolicy,
    CostBaseline,
    StrategyReadinessAssessment,
)


def _scope_matches(
    *,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID,
    scope: TenantScope,
) -> bool:
    if tenant_id != scope.tenant_id or data_domain_id != scope.data_domain_id:
        return False
    if project_id is not None and not scope.all_projects and project_id not in scope.project_ids:
        return False
    if not scope.all_decision_units and decision_unit_id not in scope.decision_unit_ids:
        return False
    return True


class CommercialRepository(Protocol):
    def upsert_cost(self, item: CostBaseline) -> None: ...
    def get_cost(self, *, scope: TenantScope, cost_baseline_id: UUID) -> CostBaseline | None: ...
    def list_costs(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[CostBaseline, ...]: ...
    def upsert_policy(self, item: CommercialPolicy) -> None: ...
    def get_policy(self, *, scope: TenantScope, policy_id: UUID) -> CommercialPolicy | None: ...
    def list_policies(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[CommercialPolicy, ...]: ...
    def upsert_readiness(self, item: StrategyReadinessAssessment) -> None: ...
    def get_readiness(
        self, *, scope: TenantScope, readiness_id: UUID
    ) -> StrategyReadinessAssessment | None: ...
    def list_readiness(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[StrategyReadinessAssessment, ...]: ...


class InMemoryCommercialRepository:
    def __init__(self) -> None:
        self._costs: dict[UUID, CostBaseline] = {}
        self._policies: dict[UUID, CommercialPolicy] = {}
        self._readiness: dict[UUID, StrategyReadinessAssessment] = {}
        self._lock = threading.Lock()

    def upsert_cost(self, item: CostBaseline) -> None:
        with self._lock:
            self._costs[item.cost_baseline_id] = item

    def get_cost(self, *, scope: TenantScope, cost_baseline_id: UUID) -> CostBaseline | None:
        with self._lock:
            item = self._costs.get(cost_baseline_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_costs(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[CostBaseline, ...]:
        with self._lock:
            items = [
                item
                for item in self._costs.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.cost_baseline_id)))
        return tuple(items)

    def upsert_policy(self, item: CommercialPolicy) -> None:
        with self._lock:
            self._policies[item.policy_id] = item

    def get_policy(self, *, scope: TenantScope, policy_id: UUID) -> CommercialPolicy | None:
        with self._lock:
            item = self._policies.get(policy_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_policies(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[CommercialPolicy, ...]:
        with self._lock:
            items = [
                item
                for item in self._policies.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.policy_id)))
        return tuple(items)

    def upsert_readiness(self, item: StrategyReadinessAssessment) -> None:
        with self._lock:
            self._readiness[item.readiness_id] = item

    def get_readiness(
        self, *, scope: TenantScope, readiness_id: UUID
    ) -> StrategyReadinessAssessment | None:
        with self._lock:
            item = self._readiness.get(readiness_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_readiness(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[StrategyReadinessAssessment, ...]:
        with self._lock:
            items = [
                item
                for item in self._readiness.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.readiness_id)))
        return tuple(items)
