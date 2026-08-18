"""SQLAlchemy adapter for FR-01. Member 2 exclusive; does not touch other modules."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from biaice.core.auth import TenantScope
from biaice.core.db import tenant_transaction
from biaice.modules.projects.application.repository import _scope_ok
from biaice.modules.projects.domain.models import (
    DecisionUnit,
    DecisionUnitLifecycleEvent,
    DocumentIntakeRef,
    ProcurementProject,
)
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
from biaice.modules.rules.domain.models import (
    ApplicableRegime,
    ComplianceReview,
    CrossLotConstraint,
    RuleClause,
    RuleScopeLevel,
    RuleSet,
    ScopeAssessment,
)

T = TypeVar("T")


def _write_scope(item: object) -> TenantScope:
    return TenantScope(
        tenant_id=item.tenant_id,  # type: ignore[attr-defined]
        data_domain_id=item.data_domain_id,  # type: ignore[attr-defined]
        all_projects=True,
        all_decision_units=True,
    )


class SqlAlchemyFr01Repository:
    """PostgreSQL (and sqlite-in-test) persistence for FR-01 aggregates."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _tx(self, scope: TenantScope) -> Iterator[Session]:
        session = self._session_factory()
        try:
            with tenant_transaction(session, scope):
                yield session
                # Flush before tenant_transaction pops the bound scope on exit.
                session.flush()
        finally:
            session.close()

    def upsert_project(self, item: ProcurementProject) -> None:
        with self._tx(_write_scope(item)) as session:
            row = session.get(ProcurementProjectRow, item.project_id) or ProcurementProjectRow(
                project_id=item.project_id
            )
            row.tenant_id = item.tenant_id
            row.data_domain_id = item.data_domain_id
            row.project_id = item.project_id
            row.decision_unit_id = None
            row.created_at = item.version.created_at
            row.body = item.model_dump(mode="json")
            session.add(row)

    def get_project(self, *, scope: TenantScope, project_id: UUID) -> ProcurementProject | None:
        with self._tx(scope) as session:
            row = session.get(ProcurementProjectRow, project_id)
            if row is None:
                return None
            item = ProcurementProject.model_validate(row.body)
        if not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=None,
            scope=scope,
        ):
            return None
        return item

    def list_projects(self, *, scope: TenantScope) -> tuple[ProcurementProject, ...]:
        with self._tx(scope) as session:
            rows = session.query(ProcurementProjectRow).all()
            items = [ProcurementProject.model_validate(row.body) for row in rows]
        return tuple(
            sorted(
                (
                    item
                    for item in items
                    if _scope_ok(
                        tenant_id=item.tenant_id,
                        data_domain_id=item.data_domain_id,
                        project_id=item.project_id,
                        decision_unit_id=None,
                        scope=scope,
                    )
                ),
                key=lambda item: (item.version.created_at, str(item.project_id)),
            )
        )

    def upsert_unit(self, item: DecisionUnit) -> None:
        with self._tx(_write_scope(item)) as session:
            row = session.get(DecisionUnitRow, item.decision_unit_id) or DecisionUnitRow(
                decision_unit_id=item.decision_unit_id
            )
            row.tenant_id = item.tenant_id
            row.data_domain_id = item.data_domain_id
            row.project_id = item.project_id
            row.decision_unit_id = item.decision_unit_id
            row.created_at = item.version.created_at
            row.body = item.model_dump(mode="json")
            session.add(row)

    def get_unit(self, *, scope: TenantScope, unit_id: UUID) -> DecisionUnit | None:
        with self._tx(scope) as session:
            row = session.get(DecisionUnitRow, unit_id)
            if row is None:
                return None
            item = DecisionUnit.model_validate(row.body)
        if not _scope_ok(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_units(self, *, scope: TenantScope, project_id: UUID) -> tuple[DecisionUnit, ...]:
        with self._tx(scope) as session:
            rows = (
                session.query(DecisionUnitRow)
                .filter(DecisionUnitRow.project_id == project_id)
                .all()
            )
            items = [DecisionUnit.model_validate(row.body) for row in rows]
        return tuple(
            sorted(
                (
                    item
                    for item in items
                    if _scope_ok(
                        tenant_id=item.tenant_id,
                        data_domain_id=item.data_domain_id,
                        project_id=item.project_id,
                        decision_unit_id=item.decision_unit_id,
                        scope=scope,
                    )
                ),
                key=lambda item: (item.version.created_at, str(item.decision_unit_id)),
            )
        )

    def append_lifecycle_event(self, item: DecisionUnitLifecycleEvent) -> None:
        with self._tx(_write_scope(item)) as session:
            row = DecisionUnitLifecycleEventRow(
                event_id=item.event_id,
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
                project_id=item.project_id,
                decision_unit_id=item.decision_unit_id,
                sequence=item.sequence,
                body=item.model_dump(mode="json"),
            )
            session.add(row)

    def list_lifecycle_events(
        self, *, scope: TenantScope, unit_id: UUID
    ) -> tuple[DecisionUnitLifecycleEvent, ...]:
        with self._tx(scope) as session:
            rows = (
                session.query(DecisionUnitLifecycleEventRow)
                .filter(DecisionUnitLifecycleEventRow.decision_unit_id == unit_id)
                .all()
            )
            items = [DecisionUnitLifecycleEvent.model_validate(row.body) for row in rows]
        return tuple(
            sorted(
                (
                    item
                    for item in items
                    if _scope_ok(
                        tenant_id=item.tenant_id,
                        data_domain_id=item.data_domain_id,
                        project_id=item.project_id,
                        decision_unit_id=item.decision_unit_id,
                        scope=scope,
                    )
                ),
                key=lambda item: item.sequence,
            )
        )

    def upsert_scope(self, item: ScopeAssessment) -> None:
        self._upsert_body(
            item,
            ScopeAssessmentRow,
            pk="scope_assessment_id",
            created_at=item.version.created_at,
        )

    def get_scope(self, *, scope: TenantScope, scope_assessment_id: UUID) -> ScopeAssessment | None:
        return self._get_body(
            ScopeAssessment,
            ScopeAssessmentRow,
            scope_assessment_id,
            scope=scope,
            project_id_of=lambda item: item.project_id,
            unit_id_of=lambda item: item.decision_unit_id,
        )

    def list_scopes(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ScopeAssessment, ...]:
        return self._list_body(
            ScopeAssessment,
            ScopeAssessmentRow,
            scope=scope,
            unit_id=unit_id,
            created_at_of=lambda item: item.version.created_at,
            id_of=lambda item: item.scope_assessment_id,
        )

    def upsert_regime(self, item: ApplicableRegime) -> None:
        self._upsert_body(
            item,
            ApplicableRegimeRow,
            pk="applicable_regime_id",
            created_at=item.version.created_at,
        )

    def get_regime(
        self, *, scope: TenantScope, applicable_regime_id: UUID
    ) -> ApplicableRegime | None:
        return self._get_body(
            ApplicableRegime,
            ApplicableRegimeRow,
            applicable_regime_id,
            scope=scope,
            project_id_of=lambda item: item.project_id,
            unit_id_of=lambda item: item.decision_unit_id,
        )

    def list_regimes(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ApplicableRegime, ...]:
        return self._list_body(
            ApplicableRegime,
            ApplicableRegimeRow,
            scope=scope,
            unit_id=unit_id,
            created_at_of=lambda item: item.version.created_at,
            id_of=lambda item: item.applicable_regime_id,
        )

    def upsert_rule_set(self, item: RuleSet) -> None:
        with self._tx(_write_scope(item)) as session:
            row = session.get(RuleSetRow, item.rule_set_id) or RuleSetRow(
                rule_set_id=item.rule_set_id
            )
            row.tenant_id = item.tenant_id
            row.data_domain_id = item.data_domain_id
            row.project_id = item.project_id
            row.decision_unit_id = item.decision_unit_id
            row.scope_level = item.scope_level.value
            row.created_at = item.version.created_at
            row.body = item.model_dump(mode="json")
            session.add(row)

    def get_rule_set(self, *, scope: TenantScope, rule_set_id: UUID) -> RuleSet | None:
        return self._get_body(
            RuleSet,
            RuleSetRow,
            rule_set_id,
            scope=scope,
            project_id_of=lambda item: item.project_id,
            unit_id_of=lambda item: item.decision_unit_id,
        )

    def list_rule_sets(self, *, scope: TenantScope, unit_id: UUID) -> tuple[RuleSet, ...]:
        unit = self.get_unit(scope=scope, unit_id=unit_id)
        if unit is None:
            return ()
        with self._tx(scope) as session:
            rows = session.query(RuleSetRow).filter(RuleSetRow.project_id == unit.project_id).all()
            items = [RuleSet.model_validate(row.body) for row in rows]
        selected = [
            item
            for item in items
            if _scope_ok(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
                project_id=item.project_id,
                decision_unit_id=item.decision_unit_id,
                scope=scope,
            )
            and (item.decision_unit_id == unit_id or item.scope_level is RuleScopeLevel.PROJECT)
        ]
        selected.sort(key=lambda item: (item.version.created_at, str(item.rule_set_id)))
        return tuple(selected)

    def upsert_clause(self, item: RuleClause) -> None:
        with self._tx(_write_scope(item)) as session:
            row = session.get(RuleClauseRow, item.rule_clause_id) or RuleClauseRow(
                rule_clause_id=item.rule_clause_id
            )
            row.tenant_id = item.tenant_id
            row.data_domain_id = item.data_domain_id
            row.project_id = item.project_id
            row.decision_unit_id = item.decision_unit_id
            row.rule_set_id = item.rule_set_id
            row.coverage_key = item.coverage_key
            row.created_at = item.version.created_at
            row.body = item.model_dump(mode="json")
            session.add(row)

    def get_clause(self, *, scope: TenantScope, rule_clause_id: UUID) -> RuleClause | None:
        return self._get_body(
            RuleClause,
            RuleClauseRow,
            rule_clause_id,
            scope=scope,
            project_id_of=lambda item: item.project_id,
            unit_id_of=lambda item: item.decision_unit_id,
        )

    def list_clauses(self, *, scope: TenantScope, rule_set_id: UUID) -> tuple[RuleClause, ...]:
        with self._tx(scope) as session:
            rows = (
                session.query(RuleClauseRow).filter(RuleClauseRow.rule_set_id == rule_set_id).all()
            )
            items = [RuleClause.model_validate(row.body) for row in rows]
        selected = [
            item
            for item in items
            if _scope_ok(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
                project_id=item.project_id,
                decision_unit_id=item.decision_unit_id,
                scope=scope,
            )
        ]
        selected.sort(key=lambda item: (item.priority, str(item.rule_clause_id)))
        return tuple(selected)

    def list_all_clauses_for_unit(
        self, *, scope: TenantScope, unit_id: UUID
    ) -> tuple[RuleClause, ...]:
        rule_set_ids = {
            item.rule_set_id for item in self.list_rule_sets(scope=scope, unit_id=unit_id)
        }
        if not rule_set_ids:
            return ()
        with self._tx(scope) as session:
            rows = (
                session.query(RuleClauseRow)
                .filter(RuleClauseRow.rule_set_id.in_(rule_set_ids))
                .all()
            )
            items = [RuleClause.model_validate(row.body) for row in rows]
        selected = [
            item
            for item in items
            if _scope_ok(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
                project_id=item.project_id,
                decision_unit_id=item.decision_unit_id,
                scope=scope,
            )
        ]
        selected.sort(key=lambda item: (item.coverage_key, item.priority, str(item.rule_clause_id)))
        return tuple(selected)

    def upsert_review(self, item: ComplianceReview) -> None:
        self._upsert_body(
            item,
            ComplianceReviewRow,
            pk="compliance_review_id",
            created_at=item.version.created_at,
        )

    def get_review(
        self, *, scope: TenantScope, compliance_review_id: UUID
    ) -> ComplianceReview | None:
        return self._get_body(
            ComplianceReview,
            ComplianceReviewRow,
            compliance_review_id,
            scope=scope,
            project_id_of=lambda item: item.project_id,
            unit_id_of=lambda item: item.decision_unit_id,
        )

    def list_reviews(self, *, scope: TenantScope, unit_id: UUID) -> tuple[ComplianceReview, ...]:
        return self._list_body(
            ComplianceReview,
            ComplianceReviewRow,
            scope=scope,
            unit_id=unit_id,
            created_at_of=lambda item: item.version.created_at,
            id_of=lambda item: item.compliance_review_id,
        )

    def upsert_constraint(self, item: CrossLotConstraint) -> None:
        self._upsert_body(
            item,
            CrossLotConstraintRow,
            pk="cross_lot_constraint_id",
            created_at=item.version.created_at,
        )

    def get_constraint(
        self, *, scope: TenantScope, cross_lot_constraint_id: UUID
    ) -> CrossLotConstraint | None:
        return self._get_body(
            CrossLotConstraint,
            CrossLotConstraintRow,
            cross_lot_constraint_id,
            scope=scope,
            project_id_of=lambda item: item.project_id,
            unit_id_of=lambda item: item.decision_unit_id,
        )

    def list_constraints(
        self, *, scope: TenantScope, unit_id: UUID
    ) -> tuple[CrossLotConstraint, ...]:
        return self._list_body(
            CrossLotConstraint,
            CrossLotConstraintRow,
            scope=scope,
            unit_id=unit_id,
            created_at_of=lambda item: item.version.created_at,
            id_of=lambda item: item.cross_lot_constraint_id,
        )

    def upsert_document_ref(self, item: DocumentIntakeRef) -> None:
        with self._tx(_write_scope(item)) as session:
            row = session.get(DocumentIntakeRefRow, item.event_id) or DocumentIntakeRefRow(
                event_id=item.event_id
            )
            row.tenant_id = item.tenant_id
            row.data_domain_id = item.data_domain_id
            row.project_id = item.project_id
            row.decision_unit_id = item.decision_unit_id
            row.event_type = item.event_type
            row.occurred_at = item.occurred_at
            row.body = item.model_dump(mode="json")
            session.add(row)

    def get_document_ref(self, *, scope: TenantScope, event_id: UUID) -> DocumentIntakeRef | None:
        with self._tx(scope) as session:
            row = session.get(DocumentIntakeRefRow, event_id)
            if row is None:
                return None
            item = DocumentIntakeRef.model_validate(row.body)
        if not _scope_ok(
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
        with self._tx(scope) as session:
            query = session.query(DocumentIntakeRefRow)
            if unit_id is not None:
                query = query.filter(DocumentIntakeRefRow.decision_unit_id == unit_id)
            rows = query.all()
            items = [DocumentIntakeRef.model_validate(row.body) for row in rows]
        selected = [
            item
            for item in items
            if _scope_ok(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
                project_id=item.project_id,
                decision_unit_id=item.decision_unit_id,
                scope=scope,
            )
        ]
        selected.sort(key=lambda item: (item.occurred_at, str(item.event_id)))
        return tuple(selected)

    def _upsert_body(self, item: object, row_type: type, *, pk: str, created_at) -> None:
        identifier = getattr(item, pk)
        with self._tx(_write_scope(item)) as session:
            row = session.get(row_type, identifier) or row_type(**{pk: identifier})
            row.tenant_id = item.tenant_id  # type: ignore[attr-defined]
            row.data_domain_id = item.data_domain_id  # type: ignore[attr-defined]
            row.project_id = item.project_id  # type: ignore[attr-defined]
            row.decision_unit_id = item.decision_unit_id  # type: ignore[attr-defined]
            row.created_at = created_at
            row.body = item.model_dump(mode="json")  # type: ignore[attr-defined]
            session.add(row)

    def _get_body(
        self,
        model: type[T],
        row_type: type,
        identifier: UUID,
        *,
        scope: TenantScope,
        project_id_of: Callable[[T], UUID],
        unit_id_of: Callable[[T], UUID],
    ) -> T | None:
        with self._tx(scope) as session:
            row = session.get(row_type, identifier)
            if row is None:
                return None
            item = model.model_validate(row.body)
        if not _scope_ok(
            tenant_id=item.tenant_id,  # type: ignore[attr-defined]
            data_domain_id=item.data_domain_id,  # type: ignore[attr-defined]
            project_id=project_id_of(item),
            decision_unit_id=unit_id_of(item),
            scope=scope,
        ):
            return None
        return item

    def _list_body(
        self,
        model: type[T],
        row_type: type,
        *,
        scope: TenantScope,
        unit_id: UUID,
        created_at_of: Callable[[T], object],
        id_of: Callable[[T], UUID],
    ) -> tuple[T, ...]:
        with self._tx(scope) as session:
            rows = session.query(row_type).filter(row_type.decision_unit_id == unit_id).all()
            items = [model.model_validate(row.body) for row in rows]
        selected = [
            item
            for item in items
            if _scope_ok(
                tenant_id=item.tenant_id,  # type: ignore[attr-defined]
                data_domain_id=item.data_domain_id,  # type: ignore[attr-defined]
                project_id=item.project_id,  # type: ignore[attr-defined]
                decision_unit_id=item.decision_unit_id,  # type: ignore[attr-defined]
                scope=scope,
            )
        ]
        selected.sort(key=lambda item: (created_at_of(item), str(id_of(item))))
        return tuple(selected)
