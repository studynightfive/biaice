from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict

from biaice.core.security.gates import GateName

router = APIRouter(tags=["health"])


class ComponentHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    status: Literal["UP", "DOWN", "DEGRADED", "DISABLED"]
    detail: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["UP", "DOWN", "DEGRADED"]
    ready: bool
    mode: Literal["SYNTHETIC_ONLY", "REAL_DATA"]
    checked_at: datetime
    version: str
    components: tuple[ComponentHealth, ...]


@router.get(
    "/health/live",
    operation_id="get_liveness",
    response_model=HealthResponse,
    summary="Process liveness without business data or authentication",
)
def live(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="UP",
        ready=True,
        mode="REAL_DATA" if settings.real_data_mode_requested else "SYNTHETIC_ONLY",
        checked_at=datetime.now(timezone.utc),
        version=settings.application_version,
        components=(ComponentHealth(name="process", status="UP"),),
    )


@router.get(
    "/health/ready",
    operation_id="get_readiness",
    response_model=HealthResponse,
    summary="Readiness; never discloses secrets or business data",
)
def ready(request: Request, response: Response) -> HealthResponse:
    settings = request.app.state.settings
    checks = request.app.state.readiness_checks
    components = tuple(check() for check in checks)
    gates = request.app.state.gate_service
    real_gate = gates.current(GateName.REAL_DATA_MODE)
    byok_gate = gates.current(GateName.BYOK_SECRET_GATE)
    components += (
        ComponentHealth(
            name="audit_sink",
            status=(
                "UP"
                if request.app.state.audit_writer.available
                else ("DOWN" if settings.audit_sink_required else "DISABLED")
            ),
            detail=(
                None
                if request.app.state.audit_writer.available
                else "append-only audit writer unavailable"
            ),
        ),
        ComponentHealth(
            name="real_data_mode",
            status="UP" if real_gate.is_pass_current else "DISABLED",
            detail=f"{real_gate.status}/{real_gate.validity}",
        ),
        ComponentHealth(
            name="byok_secret_gate",
            status="UP" if byok_gate.is_pass_current else "DISABLED",
            detail=f"{byok_gate.status}/{byok_gate.validity}",
        ),
    )
    ready_value = all(component.status != "DOWN" for component in components)
    if settings.real_data_mode_requested:
        ready_value = ready_value and real_gate.is_pass_current
    if settings.byok_enabled:
        ready_value = ready_value and byok_gate.is_pass_current
    if not ready_value:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    aggregate_status = (
        "DOWN"
        if not ready_value
        else (
            "DEGRADED"
            if any(component.status == "DEGRADED" for component in components)
            else "UP"
        )
    )
    return HealthResponse(
        status=aggregate_status,
        ready=ready_value,
        mode="REAL_DATA" if settings.real_data_mode_requested else "SYNTHETIC_ONLY",
        checked_at=datetime.now(timezone.utc),
        version=settings.application_version,
        components=components,
    )
