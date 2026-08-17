"""FR-01 SQLAlchemy 2 tables (member 2). JSON body keeps domain models authoritative."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from biaice.core.db import Base, TenantScopedMixin


class ProcurementProjectRow(Base, TenantScopedMixin):
    __tablename__ = "procurement_project"

    project_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class DecisionUnitRow(Base, TenantScopedMixin):
    __tablename__ = "decision_unit"

    decision_unit_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class DecisionUnitLifecycleEventRow(Base, TenantScopedMixin):
    __tablename__ = "decision_unit_lifecycle_event"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "sequence",
            name="uq_lifecycle_event_sequence",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class ScopeAssessmentRow(Base, TenantScopedMixin):
    __tablename__ = "scope_assessment"

    scope_assessment_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class ApplicableRegimeRow(Base, TenantScopedMixin):
    __tablename__ = "applicable_regime"

    applicable_regime_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class RuleSetRow(Base, TenantScopedMixin):
    __tablename__ = "rule_set"

    rule_set_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope_level: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class RuleClauseRow(Base, TenantScopedMixin):
    __tablename__ = "rule_clause"

    rule_clause_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    rule_set_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    coverage_key: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class ComplianceReviewRow(Base, TenantScopedMixin):
    __tablename__ = "compliance_review"

    compliance_review_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class CrossLotConstraintRow(Base, TenantScopedMixin):
    __tablename__ = "cross_lot_constraint"

    cross_lot_constraint_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)


class DocumentIntakeRefRow(Base, TenantScopedMixin):
    __tablename__ = "document_intake_ref"

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body: Mapped[dict] = mapped_column(JSON, nullable=False)
