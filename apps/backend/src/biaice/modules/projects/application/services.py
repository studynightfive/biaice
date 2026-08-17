"""Application services for member-2 FR-01 projects and lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec, assert_etag, compute_etag
from biaice.core.money import Money
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.core.versioning import VersionMetadata
from biaice.modules.projects.application.pagination import paginate
from biaice.modules.projects.application.repository import (
    Fr01Repository,
    InMemoryFr01Repository,
)
from biaice.modules.projects.domain.lifecycle import (
    DecisionUnitLifecycleState,
    resolve_transition,
)
from biaice.modules.projects.domain.models import (
    DecisionUnit,
    DecisionUnitLifecycleEvent,
    ProcurementProject,
    ResourceLifecycle,
    ResourceValidity,
    canonical_hash,
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
    project_id: UUID | None = None,
    decision_unit_id: UUID | None = None,
) -> None:
    if outbox_port is None:
        return
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
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


def _version(
    *,
    actor_id: UUID,
    now: datetime,
    payload: Mapping[str, Any],
    number: int = 1,
    supersedes: UUID | None = None,
) -> VersionMetadata:
    return VersionMetadata(
        version_id=uuid4(),
        version_number=number,
        created_at=now,
        created_by=actor_id,
        content_hash=canonical_hash(payload),
        supersedes_version_id=supersedes,
    )


def require_unit(repository: Fr01Repository, identity: IdentityContext, unit_id: UUID) -> DecisionUnit:
    identity.scope.assert_allows(
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        decision_unit_id=unit_id,
    )
    item = repository.get_unit(scope=identity.scope, unit_id=unit_id)
    if item is None:
        raise BiaiceError("RESOURCE_NOT_FOUND", detail=f"DecisionUnit {unit_id} not found in scope.")
    return item


def require_project(
    repository: Fr01Repository, identity: IdentityContext, project_id: UUID
) -> ProcurementProject:
    identity.scope.assert_allows(
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=project_id,
    )
    item = repository.get_project(scope=identity.scope, project_id=project_id)
    if item is None:
        raise BiaiceError("RESOURCE_NOT_FOUND", detail=f"Project {project_id} not found in scope.")
    return item


class ProjectService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
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
        name: str,
        purchaser_name: str,
        timezone: str,
        budget: Money | None,
        price_ceiling: Money | None,
        deadline_at: datetime | None,
        cross_unit_group_id: UUID | None,
        notes: str | None,
        request_id: str,
    ) -> ProcurementProject:
        require_audit(self.audit_writer)
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
        )
        now = self.clock.now()
        project_id = uuid4()
        payload = {
            "name": name,
            "purchaser_name": purchaser_name,
            "timezone": timezone,
            "budget": None if budget is None else budget.model_dump(mode="json"),
            "price_ceiling": None if price_ceiling is None else price_ceiling.model_dump(mode="json"),
            "deadline_at": None if deadline_at is None else deadline_at.isoformat(),
            "cross_unit_group_id": None if cross_unit_group_id is None else str(cross_unit_group_id),
            "notes": notes,
        }
        item = ProcurementProject(
            project_id=project_id,
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            name=name,
            purchaser_name=purchaser_name,
            timezone=timezone,
            budget=budget,
            price_ceiling=price_ceiling,
            deadline_at=deadline_at,
            cross_unit_group_id=cross_unit_group_id,
            notes=notes,
            lifecycle_state=ResourceLifecycle.DRAFT,
            validity_state=ResourceValidity.CURRENT,
            version=_version(actor_id=identity.subject_id, now=now, payload=payload),
        )
        self.repository.upsert_project(item)
        self.audit_writer.write(
            identity=identity,
            action="projects.project.create",
            object_type="ProcurementProject",
            object_id=item.project_id,
            request_id=request_id,
            reason_code="PROJECT_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(
        self,
        *,
        identity: IdentityContext,
        cursor: str | None = None,
        limit: int | None = None,
        codec: CursorCodec | None = None,
    ) -> tuple[tuple[ProcurementProject, ...], str | None, bool]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
        )
        items = self.repository.list_projects(scope=identity.scope)
        return paginate(
            items,
            scope=identity.scope,
            codec=codec,
            cursor=cursor,
            limit=limit,
            sort_key=lambda item: item.version.created_at.isoformat(),
            tie_breaker=lambda item: str(item.project_id),
        )

    def get(self, *, identity: IdentityContext, project_id: UUID) -> ProcurementProject:
        return require_project(self.repository, identity, project_id)

    def update_draft(
        self,
        *,
        identity: IdentityContext,
        project_id: UUID,
        if_match: str,
        name: str | None,
        purchaser_name: str | None,
        timezone: str | None,
        budget: Money | None,
        price_ceiling: Money | None,
        deadline_at: datetime | None,
        cross_unit_group_id: UUID | None,
        notes: str | None,
        request_id: str,
    ) -> ProcurementProject:
        require_audit(self.audit_writer)
        current = require_project(self.repository, identity, project_id)
        if current.lifecycle_state is not ResourceLifecycle.DRAFT:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Only DRAFT projects can be patched; archive or create a successor.",
            )
        assert_etag(compute_etag(current.version.content_hash), if_match)
        now = self.clock.now()
        updated = current.model_copy(
            update={
                "name": name or current.name,
                "purchaser_name": purchaser_name or current.purchaser_name,
                "timezone": timezone or current.timezone,
                "budget": current.budget if budget is None else budget,
                "price_ceiling": current.price_ceiling if price_ceiling is None else price_ceiling,
                "deadline_at": current.deadline_at if deadline_at is None else deadline_at,
                "cross_unit_group_id": current.cross_unit_group_id
                if cross_unit_group_id is None
                else cross_unit_group_id,
                "notes": current.notes if notes is None else notes,
                "version": _version(
                    actor_id=identity.subject_id,
                    now=now,
                    payload={"name": name or current.name, "notes": notes},
                    number=current.version.version_number + 1,
                    supersedes=current.version.version_id,
                ),
            }
        )
        self.repository.upsert_project(updated)
        self.audit_writer.write(
            identity=identity,
            action="projects.project.update_draft",
            object_type="ProcurementProject",
            object_id=updated.project_id,
            request_id=request_id,
            reason_code="PROJECT_DRAFT_UPDATED",
            outcome=updated.lifecycle_state.value,
            object_version_id=updated.version.version_id,
        )
        return updated

    def archive(self, *, identity: IdentityContext, project_id: UUID, request_id: str) -> ProcurementProject:
        require_audit(self.audit_writer)
        current = require_project(self.repository, identity, project_id)
        now = self.clock.now()
        archived = current.model_copy(
            update={
                "lifecycle_state": ResourceLifecycle.ARCHIVED,
                "validity_state": ResourceValidity.STALE,
                "archived_at": now,
                "archived_by": identity.subject_id,
            }
        )
        self.repository.upsert_project(archived)
        self.audit_writer.write(
            identity=identity,
            action="projects.project.archive",
            object_type="ProcurementProject",
            object_id=archived.project_id,
            request_id=request_id,
            reason_code="PROJECT_ARCHIVED",
            outcome=archived.lifecycle_state.value,
            object_version_id=archived.version.version_id,
        )
        return archived


class DecisionUnitService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
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
        project_id: UUID,
        name: str,
        lot_code: str | None,
        timezone: str,
        budget: Money | None,
        price_ceiling: Money | None,
        deadline_at: datetime | None,
        cross_unit_group_id: UUID | None,
        request_id: str,
    ) -> DecisionUnit:
        require_audit(self.audit_writer)
        project = require_project(self.repository, identity, project_id)
        now = self.clock.now()
        unit_id = uuid4()
        payload = {"name": name, "lot_code": lot_code, "timezone": timezone}
        item = DecisionUnit(
            decision_unit_id=unit_id,
            project_id=project.project_id,
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            name=name,
            lot_code=lot_code,
            timezone=timezone,
            budget=budget,
            price_ceiling=price_ceiling,
            deadline_at=deadline_at,
            cross_unit_group_id=cross_unit_group_id or project.cross_unit_group_id,
            lifecycle_state=DecisionUnitLifecycleState.DRAFT,
            resource_lifecycle=ResourceLifecycle.DRAFT,
            validity_state=ResourceValidity.CURRENT,
            version=_version(actor_id=identity.subject_id, now=now, payload=payload),
            gap_summary="范围、制度与规则尚未发布；不得显示正式 GO。",
        )
        self.repository.upsert_unit(item)
        self.audit_writer.write(
            identity=identity,
            action="projects.decision_unit.create",
            object_type="DecisionUnit",
            object_id=item.decision_unit_id,
            request_id=request_id,
            reason_code="DECISION_UNIT_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(
        self,
        *,
        identity: IdentityContext,
        project_id: UUID,
        cursor: str | None = None,
        limit: int | None = None,
        codec: CursorCodec | None = None,
    ) -> tuple[tuple[DecisionUnit, ...], str | None, bool]:
        require_project(self.repository, identity, project_id)
        items = self.repository.list_units(scope=identity.scope, project_id=project_id)
        return paginate(
            items,
            scope=identity.scope,
            codec=codec,
            cursor=cursor,
            limit=limit,
            sort_key=lambda item: item.version.created_at.isoformat(),
            tie_breaker=lambda item: str(item.decision_unit_id),
        )

    def get(self, *, identity: IdentityContext, unit_id: UUID) -> DecisionUnit:
        return require_unit(self.repository, identity, unit_id)

    def update_draft(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        if_match: str,
        name: str | None,
        lot_code: str | None,
        timezone: str | None,
        budget: Money | None,
        price_ceiling: Money | None,
        deadline_at: datetime | None,
        cross_unit_group_id: UUID | None,
        request_id: str,
    ) -> DecisionUnit:
        require_audit(self.audit_writer)
        current = require_unit(self.repository, identity, unit_id)
        if current.resource_lifecycle is not ResourceLifecycle.DRAFT:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Only DRAFT decision units can be patched.",
            )
        assert_etag(compute_etag(current.version.content_hash), if_match)
        now = self.clock.now()
        updated = current.model_copy(
            update={
                "name": name or current.name,
                "lot_code": current.lot_code if lot_code is None else lot_code,
                "timezone": timezone or current.timezone,
                "budget": current.budget if budget is None else budget,
                "price_ceiling": current.price_ceiling if price_ceiling is None else price_ceiling,
                "deadline_at": current.deadline_at if deadline_at is None else deadline_at,
                "cross_unit_group_id": current.cross_unit_group_id
                if cross_unit_group_id is None
                else cross_unit_group_id,
                "version": _version(
                    actor_id=identity.subject_id,
                    now=now,
                    payload={"name": name or current.name},
                    number=current.version.version_number + 1,
                    supersedes=current.version.version_id,
                ),
            }
        )
        self.repository.upsert_unit(updated)
        self.audit_writer.write(
            identity=identity,
            action="projects.decision_unit.update_draft",
            object_type="DecisionUnit",
            object_id=updated.decision_unit_id,
            request_id=request_id,
            reason_code="DECISION_UNIT_DRAFT_UPDATED",
            outcome=updated.lifecycle_state.value,
            object_version_id=updated.version.version_id,
        )
        return updated


class LifecycleService:
    """Single writer for DecisionUnitLifecycleEvent."""

    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def list_events(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        cursor: str | None = None,
        limit: int | None = None,
        codec: CursorCodec | None = None,
    ) -> tuple[tuple[DecisionUnitLifecycleEvent, ...], str | None, bool]:
        require_unit(self.repository, identity, unit_id)
        items = self.repository.list_lifecycle_events(scope=identity.scope, unit_id=unit_id)
        return paginate(
            items,
            scope=identity.scope,
            codec=codec,
            cursor=cursor,
            limit=limit,
            sort_key=lambda item: f"{item.sequence:010d}",
            tie_breaker=lambda item: str(item.event_id),
        )

    def submit(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        command: str,
        reason: str,
        basis: str | None,
        earliest_affected_stage: str | None,
        resume_state: str | None,
        request_id: str,
    ) -> DecisionUnitLifecycleEvent:
        require_audit(self.audit_writer)
        unit = require_unit(self.repository, identity, unit_id)
        resume = None
        if resume_state:
            resume = DecisionUnitLifecycleState(resume_state)
        next_state, reopened = resolve_transition(
            unit.lifecycle_state, command, resume_state=resume
        )
        if reopened and (not basis or not earliest_affected_stage):
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="REOPENED requires basis and earliest_affected_stage.",
            )
        now = self.clock.now()
        prior = self.repository.list_lifecycle_events(scope=identity.scope, unit_id=unit_id)
        event = DecisionUnitLifecycleEvent(
            event_id=uuid4(),
            decision_unit_id=unit.decision_unit_id,
            tenant_id=unit.tenant_id,
            data_domain_id=unit.data_domain_id,
            project_id=unit.project_id,
            sequence=len(prior) + 1,
            command=command.strip().upper(),
            from_state=unit.lifecycle_state,
            to_state=next_state,
            reopened=reopened,
            reason=reason,
            basis=basis,
            earliest_affected_stage=earliest_affected_stage,
            actor_id=identity.subject_id,
            occurred_at=now,
            request_id=request_id,
        )
        self.repository.append_lifecycle_event(event)
        self.repository.upsert_unit(unit.model_copy(update={"lifecycle_state": next_state}))
        event_type = (
            "rules.decision_unit_reopened.v1"
            if reopened
            else "rules.decision_unit_lifecycle_advanced.v1"
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type=event_type,
            aggregate_type="DecisionUnit",
            aggregate_id=unit.decision_unit_id,
            payload={
                "decision_unit_id": str(unit.decision_unit_id),
                "from_state": event.from_state.value,
                "to_state": event.to_state.value,
                "command": event.command,
                "reopened": reopened,
                "earliest_affected_stage": earliest_affected_stage,
            },
            request_id=request_id,
            project_id=unit.project_id,
            decision_unit_id=unit.decision_unit_id,
        )
        self.audit_writer.write(
            identity=identity,
            action="projects.lifecycle.submit",
            object_type="DecisionUnitLifecycleEvent",
            object_id=event.event_id,
            request_id=request_id,
            reason_code=event.command,
            outcome=event.to_state.value,
            object_version_id=unit.version.version_id,
        )
        return event

    def submit_after_intake(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        command: str,
        reason: str,
        basis: str | None,
        earliest_affected_stage: str | None,
        request_id: str,
    ) -> DecisionUnitLifecycleEvent:
        """Move DRAFT/DOCUMENTS_PARSING to REGIME_AND_SCOPE_PENDING, then apply command."""
        unit = require_unit(self.repository, identity, unit_id)
        if unit.lifecycle_state.value == command.strip().upper():
            events = self.list_events(identity=identity, unit_id=unit_id)
            if events:
                return events[-1]
        if unit.lifecycle_state in {
            DecisionUnitLifecycleState.DRAFT,
            DecisionUnitLifecycleState.DOCUMENTS_PARSING,
        }:
            self.submit(
                identity=identity,
                unit_id=unit_id,
                command=DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING.value,
                reason="intake complete before scope/constraint command",
                basis=basis,
                earliest_affected_stage="REGIME_AND_SCOPE_PENDING",
                resume_state=None,
                request_id=request_id,
            )
        return self.submit(
            identity=identity,
            unit_id=unit_id,
            command=command,
            reason=reason,
            basis=basis,
            earliest_affected_stage=earliest_affected_stage,
            resume_state=None,
            request_id=request_id,
        )


class ProjectsServices:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.projects = ProjectService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.units = DecisionUnitService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.lifecycle = LifecycleService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )


def configure_fr01(
    app, *, repository: Fr01Repository | None = None
) -> ProjectsServices:
    """Attach member-2 project/rule services to the FastAPI app state."""
    from biaice.modules.projects.application.document_events import DocumentEventConsumer
    from biaice.modules.projects.infrastructure.sql_repository import SqlAlchemyFr01Repository
    from biaice.modules.rules.application.services import RulesServices

    if repository is None:
        session_factory = getattr(app.state, "session_factory", None)
        if session_factory is not None:
            repository = SqlAlchemyFr01Repository(session_factory)
        else:
            repository = InMemoryFr01Repository()
    clock = SystemClock()
    audit_writer = app.state.audit_writer
    outbox_port = getattr(app.state, "outbox_port", None)
    projects = ProjectsServices(
        repository=repository,
        clock=clock,
        audit_writer=audit_writer,
        outbox_port=outbox_port,
    )
    rules = RulesServices(
        repository=repository,
        clock=clock,
        audit_writer=audit_writer,
        outbox_port=outbox_port,
        lifecycle=projects.lifecycle,
    )
    app.state.fr01_repository = repository
    app.state.projects_services = projects
    app.state.rules_services = rules
    app.state.fr01_document_events = DocumentEventConsumer(repository)
    return projects
