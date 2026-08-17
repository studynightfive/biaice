"""FR-01 repository port and in-memory test double (member 2)."""

from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.projects.domain.models import (
    DecisionUnit,
    DecisionUnitLifecycleEvent,
    DocumentIntakeRef,
    ProcurementProject,
)
from biaice.modules.rules.domain.models import (
    ApplicableRegime,
    ComplianceReview,
    CrossLotConstraint,
    RuleClause,
    RuleScopeLevel,
    RuleSet,
    ScopeAssessment,
)


def _scope_ok(
    *,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID | None,
    scope: TenantScope,
) -> bool:
    if tenant_id != scope.tenant_id or data_domain_id != scope.data_domain_id:
        return False
    if (
        project_id is not None
        and not scope.all_projects
        and scope.project_ids
        and project_id not in scope.project_ids
    ):
        return False
    if (
        decision_unit_id is not None
        and not scope.all_decision_units
        and scope.decision_unit_ids
        and decision_unit_id not in scope.decision_unit_ids
    ):
        return False
    return True


class Fr01Repository(Protocol):
    def upsert_project(self, item: ProcurementProject) -> None: ...
    def get_project(self, *, scope: TenantScope, project_id: UUID) -> ProcurementProject | None: ...
    def list_projects(self, *, scope: TenantScope) -> tuple[ProcurementProject, ...]: ...
    def upsert_unit(self, item: DecisionUnit) -> None: ...
    def get_unit(self, *, scope: TenantScope, unit_id: UUID) -> DecisionUnit | None: ...
    def list_units(self, *, scope: TenantScope, project_id: UUID) -> tuple[DecisionUnit, ...]: ...
    def append_lifecycle_event(self, item: DecisionUnitLifecycleEvent) -> None: ...
    def list_lifecycle_events(
        self, *, scope: TenantScope, unit_id: UUID
    ) -> tuple[DecisionUnitLifecycleEvent, ...]: ...
    def upsert_scope(self, item: ScopeAssessment) -> None: ...
    def get_scope(self, *, scope: TenantScope, scope_assessment_id: UUID) -> ScopeAssessment | None: ...
    def list_scopes(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ScopeAssessment, ...]: ...
    def upsert_regime(self, item: ApplicableRegime) -> None: ...
    def get_regime(self, *, scope: TenantScope, applicable_regime_id: UUID) -> ApplicableRegime | None: ...
    def list_regimes(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ApplicableRegime, ...]: ...
    def upsert_rule_set(self, item: RuleSet) -> None: ...
    def get_rule_set(self, *, scope: TenantScope, rule_set_id: UUID) -> RuleSet | None: ...
    def list_rule_sets(self, *, scope: TenantScope, unit_id: UUID) -> tuple[RuleSet, ...]: ...
    def upsert_clause(self, item: RuleClause) -> None: ...
    def get_clause(self, *, scope: TenantScope, rule_clause_id: UUID) -> RuleClause | None: ...
    def list_clauses(self, *, scope: TenantScope, rule_set_id: UUID) -> tuple[RuleClause, ...]: ...
    def upsert_review(self, item: ComplianceReview) -> None: ...
    def get_review(self, *, scope: TenantScope, compliance_review_id: UUID) -> ComplianceReview | None: ...
    def list_reviews(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ComplianceReview, ...]: ...
    def upsert_constraint(self, item: CrossLotConstraint) -> None: ...
    def get_constraint(
        self, *, scope: TenantScope, cross_lot_constraint_id: UUID
    ) -> CrossLotConstraint | None: ...
    def list_constraints(self, *, scope: TenantScope, unit_id: UUID) -> tuple[CrossLotConstraint, ...]: ...
    def list_all_clauses_for_unit(self, *, scope: TenantScope, unit_id: UUID) -> tuple[RuleClause, ...]: ...
    def upsert_document_ref(self, item: DocumentIntakeRef) -> None: ...
    def get_document_ref(self, *, scope: TenantScope, event_id: UUID) -> DocumentIntakeRef | None: ...
    def list_document_refs(
        self, *, scope: TenantScope, unit_id: UUID | None = None
    ) -> tuple[DocumentIntakeRef, ...]: ...


class InMemoryFr01Repository:
    """Thread-safe in-memory store used by unit tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._projects: dict[UUID, ProcurementProject] = {}
        self._units: dict[UUID, DecisionUnit] = {}
        self._events: list[DecisionUnitLifecycleEvent] = []
        self._scopes: dict[UUID, ScopeAssessment] = {}
        self._regimes: dict[UUID, ApplicableRegime] = {}
        self._rule_sets: dict[UUID, RuleSet] = {}
        self._clauses: dict[UUID, RuleClause] = {}
        self._reviews: dict[UUID, ComplianceReview] = {}
        self._constraints: dict[UUID, CrossLotConstraint] = {}
        self._document_refs: dict[UUID, DocumentIntakeRef] = {}

    def upsert_project(self, item: ProcurementProject) -> None:
        with self._lock:
            self._projects[item.project_id] = item

    def get_project(self, *, scope: TenantScope, project_id: UUID) -> ProcurementProject | None:
        with self._lock:
            item = self._projects.get(project_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=None,
            scope=scope,
        ):
            return None
        return item

    def list_projects(self, *, scope: TenantScope) -> tuple[ProcurementProject, ...]:
        with self._lock:
            items = [
                item
                for item in self._projects.values()
                if _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=None,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.project_id)))
        return tuple(items)

    def upsert_unit(self, item: DecisionUnit) -> None:
        with self._lock:
            self._units[item.decision_unit_id] = item

    def get_unit(self, *, scope: TenantScope, unit_id: UUID) -> DecisionUnit | None:
        with self._lock:
            item = self._units.get(unit_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_units(self, *, scope: TenantScope, project_id: UUID) -> tuple[DecisionUnit, ...]:
        with self._lock:
            items = [
                item
                for item in self._units.values()
                if item.project_id == project_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.decision_unit_id)))
        return tuple(items)

    def append_lifecycle_event(self, item: DecisionUnitLifecycleEvent) -> None:
        with self._lock:
            self._events.append(item)

    def list_lifecycle_events(
        self, *, scope: TenantScope, unit_id: UUID
    ) -> tuple[DecisionUnitLifecycleEvent, ...]:
        with self._lock:
            items = [
                item
                for item in self._events
                if item.decision_unit_id == unit_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: item.sequence)
        return tuple(items)

    def upsert_scope(self, item: ScopeAssessment) -> None:
        with self._lock:
            self._scopes[item.scope_assessment_id] = item

    def get_scope(self, *, scope: TenantScope, scope_assessment_id: UUID) -> ScopeAssessment | None:
        with self._lock:
            item = self._scopes.get(scope_assessment_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_scopes(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ScopeAssessment, ...]:
        with self._lock:
            items = [
                item
                for item in self._scopes.values()
                if item.decision_unit_id == unit_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.scope_assessment_id)))
        return tuple(items)

    def upsert_regime(self, item: ApplicableRegime) -> None:
        with self._lock:
            self._regimes[item.applicable_regime_id] = item

    def get_regime(self, *, scope: TenantScope, applicable_regime_id: UUID) -> ApplicableRegime | None:
        with self._lock:
            item = self._regimes.get(applicable_regime_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_regimes(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ApplicableRegime, ...]:
        with self._lock:
            items = [
                item
                for item in self._regimes.values()
                if item.decision_unit_id == unit_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.applicable_regime_id)))
        return tuple(items)

    def upsert_rule_set(self, item: RuleSet) -> None:
        with self._lock:
            self._rule_sets[item.rule_set_id] = item

    def get_rule_set(self, *, scope: TenantScope, rule_set_id: UUID) -> RuleSet | None:
        with self._lock:
            item = self._rule_sets.get(rule_set_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_rule_sets(self, *, scope: TenantScope, unit_id: UUID) -> tuple[RuleSet, ...]:
        unit = self.get_unit(scope=scope, unit_id=unit_id)
        if unit is None:
            return ()
        with self._lock:
            items = [
                item
                for item in self._rule_sets.values()
                if _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.project_id == unit.project_id
                and (
                    item.decision_unit_id == unit_id
                    or item.scope_level is RuleScopeLevel.PROJECT
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.rule_set_id)))
        return tuple(items)

    def upsert_clause(self, item: RuleClause) -> None:
        with self._lock:
            self._clauses[item.rule_clause_id] = item

    def get_clause(self, *, scope: TenantScope, rule_clause_id: UUID) -> RuleClause | None:
        with self._lock:
            item = self._clauses.get(rule_clause_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_clauses(self, *, scope: TenantScope, rule_set_id: UUID) -> tuple[RuleClause, ...]:
        with self._lock:
            items = [
                item
                for item in self._clauses.values()
                if item.rule_set_id == rule_set_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.priority, str(item.rule_clause_id)))
        return tuple(items)

    def list_all_clauses_for_unit(
        self, *, scope: TenantScope, unit_id: UUID
    ) -> tuple[RuleClause, ...]:
        rule_set_ids = {item.rule_set_id for item in self.list_rule_sets(scope=scope, unit_id=unit_id)}
        with self._lock:
            items = [
                item
                for item in self._clauses.values()
                if item.rule_set_id in rule_set_ids
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.coverage_key, item.priority, str(item.rule_clause_id)))
        return tuple(items)

    def upsert_review(self, item: ComplianceReview) -> None:
        with self._lock:
            self._reviews[item.compliance_review_id] = item

    def get_review(self, *, scope: TenantScope, compliance_review_id: UUID) -> ComplianceReview | None:
        with self._lock:
            item = self._reviews.get(compliance_review_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_reviews(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ComplianceReview, ...]:
        with self._lock:
            items = [
                item
                for item in self._reviews.values()
                if item.decision_unit_id == unit_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.compliance_review_id)))
        return tuple(items)

    def upsert_constraint(self, item: CrossLotConstraint) -> None:
        with self._lock:
            self._constraints[item.cross_lot_constraint_id] = item

    def get_constraint(
        self, *, scope: TenantScope, cross_lot_constraint_id: UUID
    ) -> CrossLotConstraint | None:
        with self._lock:
            item = self._constraints.get(cross_lot_constraint_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_constraints(self, *, scope: TenantScope, unit_id: UUID) -> tuple[CrossLotConstraint, ...]:
        with self._lock:
            items = [
                item
                for item in self._constraints.values()
                if item.decision_unit_id == unit_id
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.version.created_at, str(item.cross_lot_constraint_id)))
        return tuple(items)

    def upsert_document_ref(self, item: DocumentIntakeRef) -> None:
        with self._lock:
            self._document_refs[item.event_id] = item

    def get_document_ref(self, *, scope: TenantScope, event_id: UUID) -> DocumentIntakeRef | None:
        with self._lock:
            item = self._document_refs.get(event_id)
        if item is None or not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_document_refs(
        self, *, scope: TenantScope, unit_id: UUID | None = None
    ) -> tuple[DocumentIntakeRef, ...]:
        with self._lock:
            items = [
                item
                for item in self._document_refs.values()
                if (unit_id is None or item.decision_unit_id == unit_id)
                and _scope_ok(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
            ]
        items.sort(key=lambda item: (item.occurred_at, str(item.event_id)))
        return tuple(items)
