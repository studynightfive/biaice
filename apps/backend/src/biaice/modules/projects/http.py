"""FR-01 member-2 projects, decision units and lifecycle router."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from biaice.core.auth import IdentityContext
from biaice.core.errors import PROBLEM_RESPONSES
from biaice.core.http import CursorCodec, require_if_match
from biaice.core.idempotency import require_idempotency_key
from biaice.core.money import Money
from biaice.modules.projects.application.authz import Fr01Guard
from biaice.modules.projects.application.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from biaice.modules.projects.application.services import (
    DecisionUnitService,
    LifecycleService,
    ProjectService,
    ProjectsServices,
)
from biaice.modules.projects.domain.models import (
    DecisionUnit,
    DecisionUnitLifecycleEvent,
    ProcurementProject,
)

router = APIRouter(prefix="/api/v1", tags=["projects"])


def _datetime_input(value: Any) -> Any:
    if isinstance(value, (str, datetime)):
        return value
    raise ValueError("datetime must be an ISO-8601 string")


StrictDateTime = Annotated[datetime, BeforeValidator(_datetime_input)]


def get_projects_services(request: Request) -> ProjectsServices:
    services = getattr(request.app.state, "projects_services", None)
    if services is None:
        from biaice.core.errors import BiaiceError

        raise BiaiceError("INTERNAL_ERROR", detail="FR-01 project services are not configured.")
    return services


def get_project_service(request: Request) -> ProjectService:
    return get_projects_services(request).projects


def get_unit_service(request: Request) -> DecisionUnitService:
    return get_projects_services(request).units


def get_lifecycle_service(request: Request) -> LifecycleService:
    return get_projects_services(request).lifecycle


def _cursor_codec(request: Request) -> CursorCodec | None:
    return getattr(request.app.state, "cursor_codec", None)


class ProjectWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    purchaser_name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(min_length=1, max_length=64)
    budget: Money | None = None
    price_ceiling: Money | None = None
    deadline_at: StrictDateTime | None = None
    cross_unit_group_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ProjectDraftPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    purchaser_name: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    budget: Money | None = None
    price_ceiling: Money | None = None
    deadline_at: StrictDateTime | None = None
    cross_unit_group_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DecisionUnitWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    lot_code: str | None = Field(default=None, max_length=80)
    timezone: str = Field(min_length=1, max_length=64)
    budget: Money | None = None
    price_ceiling: Money | None = None
    deadline_at: StrictDateTime | None = None
    cross_unit_group_id: UUID | None = None


class DecisionUnitDraftPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    lot_code: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    budget: Money | None = None
    price_ceiling: Money | None = None
    deadline_at: StrictDateTime | None = None
    cross_unit_group_id: UUID | None = None


class TransitionCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=2000)
    basis: str | None = Field(default=None, max_length=2000)
    earliest_affected_stage: str | None = Field(default=None, max_length=80)
    resume_state: str | None = Field(default=None, max_length=80)


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ProcurementProject, ...]
    next_cursor: str | None = None
    has_more: bool = False


class DecisionUnitListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[DecisionUnit, ...]
    next_cursor: str | None = None
    has_more: bool = False


class LifecycleEventListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[DecisionUnitLifecycleEvent, ...]
    next_cursor: str | None = None
    has_more: bool = False


@router.get(
    "/projects",
    operation_id="list_projects",
    response_model=ProjectListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_projects(
    request: Request,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    items, next_cursor, has_more = service.list(
        identity=identity,
        cursor=cursor,
        limit=limit,
        codec=_cursor_codec(request),
    )
    return ProjectListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/projects",
    operation_id="create_project",
    response_model=ProcurementProject,
    responses=PROBLEM_RESPONSES,
)
def create_project(
    body: ProjectWriteRequest,
    request: Request,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProjectService = Depends(get_project_service),
) -> ProcurementProject:
    del idempotency_key
    return service.create(
        identity=identity,
        name=body.name,
        purchaser_name=body.purchaser_name,
        timezone=body.timezone,
        budget=body.budget,
        price_ceiling=body.price_ceiling,
        deadline_at=body.deadline_at,
        cross_unit_group_id=body.cross_unit_group_id,
        notes=body.notes,
        request_id=request.state.request_id,
    )


@router.get(
    "/projects/{project_id}",
    operation_id="get_project",
    response_model=ProcurementProject,
    responses=PROBLEM_RESPONSES,
)
def get_project(
    project_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ProjectService = Depends(get_project_service),
) -> ProcurementProject:
    return service.get(identity=identity, project_id=project_id)


@router.patch(
    "/projects/{project_id}",
    operation_id="update_project_draft",
    response_model=ProcurementProject,
    responses=PROBLEM_RESPONSES,
)
def update_project_draft(
    body: ProjectDraftPatchRequest,
    request: Request,
    project_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    if_match: str = Depends(require_if_match),
    service: ProjectService = Depends(get_project_service),
) -> ProcurementProject:
    return service.update_draft(
        identity=identity,
        project_id=project_id,
        if_match=if_match,
        name=body.name,
        purchaser_name=body.purchaser_name,
        timezone=body.timezone,
        budget=body.budget,
        price_ceiling=body.price_ceiling,
        deadline_at=body.deadline_at,
        cross_unit_group_id=body.cross_unit_group_id,
        notes=body.notes,
        request_id=request.state.request_id,
    )


@router.post(
    "/projects/{project_id}/archive",
    operation_id="archive_project",
    response_model=ProcurementProject,
    responses=PROBLEM_RESPONSES,
)
def archive_project(
    request: Request,
    project_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProjectService = Depends(get_project_service),
) -> ProcurementProject:
    del idempotency_key
    return service.archive(
        identity=identity, project_id=project_id, request_id=request.state.request_id
    )


@router.get(
    "/projects/{project_id}/decision-units",
    operation_id="list_decision_units",
    response_model=DecisionUnitListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_decision_units(
    request: Request,
    project_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: DecisionUnitService = Depends(get_unit_service),
) -> DecisionUnitListResponse:
    items, next_cursor, has_more = service.list(
        identity=identity,
        project_id=project_id,
        cursor=cursor,
        limit=limit,
        codec=_cursor_codec(request),
    )
    return DecisionUnitListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/projects/{project_id}/decision-units",
    operation_id="create_decision_unit",
    response_model=DecisionUnit,
    responses=PROBLEM_RESPONSES,
)
def create_decision_unit(
    body: DecisionUnitWriteRequest,
    request: Request,
    project_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: DecisionUnitService = Depends(get_unit_service),
) -> DecisionUnit:
    del idempotency_key
    return service.create(
        identity=identity,
        project_id=project_id,
        name=body.name,
        lot_code=body.lot_code,
        timezone=body.timezone,
        budget=body.budget,
        price_ceiling=body.price_ceiling,
        deadline_at=body.deadline_at,
        cross_unit_group_id=body.cross_unit_group_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}",
    operation_id="get_decision_unit",
    response_model=DecisionUnit,
    responses=PROBLEM_RESPONSES,
)
def get_decision_unit(
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: DecisionUnitService = Depends(get_unit_service),
) -> DecisionUnit:
    return service.get(identity=identity, unit_id=unit_id)


@router.patch(
    "/decision-units/{unit_id}",
    operation_id="update_decision_unit_draft",
    response_model=DecisionUnit,
    responses=PROBLEM_RESPONSES,
)
def update_decision_unit_draft(
    body: DecisionUnitDraftPatchRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    if_match: str = Depends(require_if_match),
    service: DecisionUnitService = Depends(get_unit_service),
) -> DecisionUnit:
    return service.update_draft(
        identity=identity,
        unit_id=unit_id,
        if_match=if_match,
        name=body.name,
        lot_code=body.lot_code,
        timezone=body.timezone,
        budget=body.budget,
        price_ceiling=body.price_ceiling,
        deadline_at=body.deadline_at,
        cross_unit_group_id=body.cross_unit_group_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/decision-units/{unit_id}/transition-commands",
    operation_id="submit_decision_unit_transition_command",
    response_model=DecisionUnitLifecycleEvent,
    responses=PROBLEM_RESPONSES,
)
def submit_decision_unit_transition_command(
    body: TransitionCommandRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: LifecycleService = Depends(get_lifecycle_service),
) -> DecisionUnitLifecycleEvent:
    del idempotency_key
    return service.submit(
        identity=identity,
        unit_id=unit_id,
        command=body.command,
        reason=body.reason,
        basis=body.basis,
        earliest_affected_stage=body.earliest_affected_stage,
        resume_state=body.resume_state,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/lifecycle-events",
    operation_id="list_decision_unit_lifecycle_events",
    response_model=LifecycleEventListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_decision_unit_lifecycle_events(
    request: Request,
    unit_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: LifecycleService = Depends(get_lifecycle_service),
) -> LifecycleEventListResponse:
    items, next_cursor, has_more = service.list_events(
        identity=identity,
        unit_id=unit_id,
        cursor=cursor,
        limit=limit,
        codec=_cursor_codec(request),
    )
    return LifecycleEventListResponse(items=items, next_cursor=next_cursor, has_more=has_more)
