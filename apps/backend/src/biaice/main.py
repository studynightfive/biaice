"""Biaice FastAPI application factory and code-first OpenAPI source."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Callable, Sequence

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from biaice.api import approvals_reports, contract_stubs, gates, health, internal, jobs, me
from biaice.core.audit import (
    AuditWriter,
    HashChainAuditWriter,
    InMemoryAppendOnlyAuditSink,
    UnavailableAuditWriter,
)
from biaice.core.auth import Authenticator, DenyAllAuthenticator, OidcJwtAuthenticator
from biaice.core.config import Settings, get_settings
from biaice.core.errors import install_error_handlers
from biaice.core.jobs import JobPort, UnavailableJobPort
from biaice.core.readiness import build_readiness_checks
from biaice.core.security.gates import GateEvidenceProvider, GateService
from biaice.core.telemetry import (
    BYOKPreBodyGuardMiddleware,
    RequestContextMiddleware,
    ScopeOverrideMiddleware,
)


def _build_authenticator(settings: Settings) -> Authenticator:
    if settings.oidc_issuer and settings.oidc_jwks_url:
        return OidcJwtAuthenticator(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            jwks_url=settings.oidc_jwks_url,
        )
    return DenyAllAuthenticator()


def _build_audit_writer(settings: Settings) -> AuditWriter:
    if settings.environment in {"development", "test", "contract"}:
        return HashChainAuditWriter(InMemoryAppendOnlyAuditSink())
    return UnavailableAuditWriter()


def create_app(
    *,
    settings: Settings | None = None,
    authenticator: Authenticator | None = None,
    gate_evidence_provider: GateEvidenceProvider | None = None,
    audit_writer: AuditWriter | None = None,
    job_port: JobPort | None = None,
    readiness_checks: Sequence[Callable[[], health.ComponentHealth]] | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    gate_service = GateService(runtime_settings, gate_evidence_provider)
    runtime_authenticator = authenticator or _build_authenticator(runtime_settings)
    runtime_audit_writer = audit_writer or _build_audit_writer(runtime_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        # This is a startup predicate, not a UI flag. Unknown/fail/stale means
        # the secure capability cannot start.
        gate_service.assert_startup_allowed()
        if runtime_settings.real_data_mode_requested or runtime_settings.byok_enabled:
            if isinstance(runtime_authenticator, DenyAllAuthenticator):
                from biaice.core.errors import BiaiceError

                raise BiaiceError("AUTH_NOT_CONFIGURED")
            if not runtime_audit_writer.available:
                from biaice.core.errors import BiaiceError

                raise BiaiceError("AUDIT_UNAVAILABLE")
        yield

    app = FastAPI(
        title=runtime_settings.application_name,
        version=runtime_settings.application_version,
        description=(
            "Local self-hosted decision-support API. Operations tagged CONTRACT_ONLY return 501 "
            "until their owner freezes field schemas and implements the handler."
        ),
        lifespan=lifespan,
        docs_url="/api/docs" if runtime_settings.environment != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if runtime_settings.environment != "production" else None,
    )
    app.state.settings = runtime_settings
    app.state.authenticator = runtime_authenticator
    app.state.gate_service = gate_service
    app.state.audit_writer = runtime_audit_writer
    app.state.job_port = job_port or UnavailableJobPort()
    # member-7 approvals/reports services: in-memory repository + services wired here
    from biaice.modules.approvals_reports.application.services import (
        configure_approvals_reports,
    )

    configure_approvals_reports(app)
    app.state.readiness_checks = tuple(
        readiness_checks
        if readiness_checks is not None
        else build_readiness_checks(runtime_settings)
    )

    # Last added is outermost in Starlette: request ID is available to the
    # scope-spoof rejection response.
    app.add_middleware(ScopeOverrideMiddleware)
    app.add_middleware(BYOKPreBodyGuardMiddleware)
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(jobs.router)
    app.include_router(gates.router)
    # member-7 approvals/reports router MUST be registered before contract_stubs
    # so FastAPI first-match-wins routes FR-09b operations to the real handler.
    app.include_router(approvals_reports.router)
    app.include_router(contract_stubs.router)
    app.include_router(internal.router)

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["servers"] = [
            {
                "url": runtime_settings.public_origin,
                "description": "Configured local gateway origin",
            }
        ]
        schema["x-contract-source"] = "FastAPI/Pydantic v2 handlers"
        schema["x-scope-source"] = (
            "server-verified IdentityContext; client scope override forbidden"
        )
        schema["x-default-data-mode"] = "SYNTHETIC_ONLY"
        actual_owner = {
            "get_liveness": ("member-1", "PUBLIC", "public"),
            "get_readiness": ("member-1", "PUBLIC", "public"),
            "get_current_user": ("member-1", "PUBLIC", "profile:read"),
            "get_job": ("member-1", "PUBLIC", "job:read"),
            "stream_job_events": ("member-1", "PUBLIC", "job:read"),
            "cancel_job": ("member-1", "PUBLIC", "job:command"),
            "retry_job": ("member-1", "PUBLIC", "job:command"),
            "list_stage_gates": ("member-1", "PUBLIC", "gate:read"),
            "get_stage_gate": ("member-1", "PUBLIC", "gate:read"),
            "assess_stage_gate": ("member-1", "PUBLIC", "gate:assess+mfa"),
            "request_stage_gate_waiver": (
                "member-1",
                "PUBLIC",
                "gate:waiver:request+mfa",
            ),
            "decide_stage_gate_waiver": (
                "member-1",
                "PUBLIC",
                "gate:waiver:decide+mfa",
            ),
            "expire_stage_gate_waiver": (
                "member-1",
                "PUBLIC",
                "gate:waiver:decide+mfa",
            ),
            "create_risk_acceptance": ("member-7", "FR-09b", "fr-09b:create+mfa"),
            "list_risk_acceptances": ("member-7", "FR-09b", "fr-09b:read"),
            "get_risk_acceptance": ("member-7", "FR-09b", "fr-09b:read"),
            "revoke_risk_acceptance": ("member-7", "FR-09b", "fr-09b:revoke+mfa"),
            "list_manual_overrides": ("member-1", "PUBLIC", "gate:read"),
            "append_manual_override": (
                "member-1",
                "PUBLIC",
                "manual-override:append+mfa",
            ),
            "revoke_manual_override": (
                "member-1",
                "PUBLIC",
                "manual-override:append+mfa",
            ),
        }
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                operation_id = operation.get("operationId")
                if operation_id in actual_owner:
                    owner, fr, permission = actual_owner[operation_id]
                    operation.setdefault("x-contract-only", False)
                    operation.setdefault("x-owner", owner)
                    operation.setdefault("x-fr", fr)
                    operation.setdefault("x-required-permission", permission)
                for response_code, response in operation.get("responses", {}).items():
                    if not str(response_code).startswith(("4", "5")) or not isinstance(
                        response, dict
                    ):
                        continue
                    content = response.get("content", {})
                    if "application/json" in content:
                        problem_schema = content["application/json"].get("schema", {})
                        if problem_schema.get("$ref", "").endswith("/ProblemDetails"):
                            content["application/problem+json"] = content.pop("application/json")
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


app = create_app()
