"""SQLAlchemy 2 table for the member-7 RiskAcceptanceVersion slice."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from biaice.core.db import Base, TenantScopedMixin


class RiskAcceptanceRow(Base, TenantScopedMixin):
    __tablename__ = "risk_acceptance"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_risk_acceptance_scope_version",
        ),
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_risk_acceptance_scope_unit_version",
        ),
    )

    risk_acceptance_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    version_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision_unit_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    validity: Mapped[str] = mapped_column(String(20), nullable=False)
    risk: Mapped[str] = mapped_column(String(200), nullable=False)
    metric: Mapped[str] = mapped_column(String(200), nullable=False)
    acceptance_scope: Mapped[str] = mapped_column(String(400), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)
    independent_approver_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
