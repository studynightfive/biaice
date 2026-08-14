"""SQLAlchemy 2 foundation and PostgreSQL tenant-scope transaction guard."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator
from uuid import UUID

from sqlalchemy import DateTime, MetaData, Uuid, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from biaice.core.auth import TenantScope
from biaice.core.errors import BiaiceError

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {UUID: Uuid, datetime: DateTime(timezone=True)}


class TenantScopedMixin:
    """Required columns for every tenant-owned persisted object."""

    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    data_domain_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    decision_unit_id: Mapped[UUID | None] = mapped_column(
        Uuid, nullable=True, index=True
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@event.listens_for(Session, "before_flush")
def enforce_scope_on_flush(
    session: Session, flush_context: object, instances: object
) -> None:
    del flush_context, instances
    scope: TenantScope | None = session.info.get("tenant_scope")
    if scope is None:
        if any(
            isinstance(item, TenantScopedMixin)
            for item in session.new | session.dirty | session.deleted
        ):
            raise BiaiceError("TENANT_SCOPE_VIOLATION")
        return
    for item in session.new | session.dirty | session.deleted:
        if isinstance(item, TenantScopedMixin):
            scope.assert_allows(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
                project_id=item.project_id,
                decision_unit_id=item.decision_unit_id,
            )


@contextmanager
def tenant_transaction(session: Session, scope: TenantScope) -> Iterator[Session]:
    """Bind both ORM writes and PostgreSQL RLS to the authenticated scope."""

    if session.in_transaction():
        raise RuntimeError("tenant_transaction must own the transaction boundary")
    with session.begin():
        session.info["tenant_scope"] = scope
        dialect_name = session.get_bind().dialect.name
        if dialect_name == "postgresql":
            session.execute(
                text(
                    "SELECT "
                    "set_config('app.tenant_id', :tenant_id, true), "
                    "set_config('app.data_domain_id', :data_domain_id, true), "
                    "set_config('app.project_ids', :project_ids, true), "
                    "set_config('app.decision_unit_ids', :decision_unit_ids, true), "
                    "set_config('app.all_projects', :all_projects, true), "
                    "set_config('app.all_decision_units', :all_decision_units, true)"
                ),
                {
                    "tenant_id": str(scope.tenant_id),
                    "data_domain_id": str(scope.data_domain_id),
                    "project_ids": ",".join(
                        sorted(str(value) for value in scope.project_ids)
                    ),
                    "decision_unit_ids": ",".join(
                        sorted(str(value) for value in scope.decision_unit_ids)
                    ),
                    "all_projects": str(scope.all_projects).lower(),
                    "all_decision_units": str(scope.all_decision_units).lower(),
                },
            )
        elif dialect_name != "sqlite":
            raise RuntimeError(f"unsupported tenant-isolation dialect: {dialect_name}")
        try:
            yield session
        finally:
            session.info.pop("tenant_scope", None)


def assert_database_scope(session: Session, scope: TenantScope) -> None:
    bound_scope = session.info.get("tenant_scope")
    if bound_scope != scope:
        raise BiaiceError("TENANT_SCOPE_VIOLATION")
