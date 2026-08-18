"""Biaice FastAPI application factory and code-first OpenAPI source."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Callable, Sequence

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from biaice.api import (
    approvals_reports,
    contract_stubs,
    documents,
    fr05,
    gates,
    health,
    internal,
    jobs,
    market_privacy,
    me,
    model_lifecycle,
    provider_management,
    simulation,
)
from biaice.api.operation_catalog import OPERATION_CATALOG
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
from biaice.core.security.restricted_ports import SecretStorePort
from biaice.core.telemetry import (
    BYOKPreBodyGuardMiddleware,
    RequestContextMiddleware,
    ScopeOverrideMiddleware,
)
from biaice.modules.commercial import api as commercial
from biaice.modules.evidence import api as evidence
from biaice.modules.model_governance.application.provider_management import (
    ProviderRuntimePort,
)
from biaice.modules.projects.http import router as projects_router
from biaice.modules.rules.http import router as rules_router


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
    secret_store: SecretStorePort | None = None,
    provider_runtime: ProviderRuntimePort | None = None,
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
        if runtime_settings.byok_enabled:
            if secret_store is None:
                from biaice.core.errors import BiaiceError

                raise BiaiceError("SECRET_STORE_UNAVAILABLE")
            if provider_runtime is None:
                from biaice.core.errors import BiaiceError

                raise BiaiceError("EGRESS_AUTHORIZATION_UNAVAILABLE")
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

    # Configure producers before consumers so cross-member application ports
    # are bound to real fail-closed implementations at composition time.
    from biaice.modules.projects.application.services import configure_fr01

    configure_fr01(app)
    # member-7 approvals/reports services: in-memory repository + services wired here
    from biaice.modules.approvals_reports.application.services import (
        configure_approvals_reports,
    )

    configure_approvals_reports(app)
    from biaice.modules.documents.application.services import configure_documents

    configure_documents(app)
    from biaice.modules.market.application.services import (
        configure_market_privacy_services,
    )

    configure_market_privacy_services(app)
    from biaice.modules.market.privacy.application.services import (
        configure_market_privacy_services as configure_fr12_privacy_services,
    )

    configure_fr12_privacy_services(app)
    from biaice.modules.evidence.application.services import configure_evidence

    configure_evidence(app)
    from biaice.modules.commercial.application.services import configure_commercial

    configure_commercial(app)
    from biaice.modules.model_governance.application.model_lifecycle import (
        configure_model_lifecycle,
    )

    configure_model_lifecycle(app)
    from biaice.modules.model_governance.application.provider_management import (
        configure_provider_management,
    )

    configure_provider_management(
        app,
        secret_store=secret_store,
        runtime=provider_runtime,
    )

    from biaice.modules.simulation.application.services import configure_simulation

    configure_simulation(app)

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
    # Implemented member routers MUST be registered before contract_stubs
    # so FastAPI first-match-wins routes implemented operations to real handlers.
    app.include_router(projects_router)
    app.include_router(rules_router)
    app.include_router(approvals_reports.router)
    app.include_router(documents.router)
    app.include_router(evidence.router)
    app.include_router(fr05.router)
    app.include_router(market_privacy.router)
    app.include_router(commercial.router)
    app.include_router(model_lifecycle.router)
    app.include_router(provider_management.router)
    app.include_router(simulation.router)
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
            "create_project_document_upload_session": (
                "member-3",
                "FR-02",
                "fr-02:create",
            ),
            "create_unit_document_upload_session": ("member-3", "FR-02", "fr-02:create"),
            "get_document_upload_session": ("member-3", "FR-02", "fr-02:read"),
            "put_document_upload_chunk": ("member-3", "FR-02", "fr-02:put"),
            "complete_document_upload_session": ("member-3", "FR-02", "fr-02:complete"),
            "cancel_document_upload_session": ("member-3", "FR-02", "fr-02:cancel"),
            "list_project_documents": ("member-3", "FR-02", "fr-02:read"),
            "list_unit_documents": ("member-3", "FR-02", "fr-02:read"),
            "get_document": ("member-3", "FR-02", "fr-02:read"),
            "review_document": ("member-3", "FR-02", "fr-02:review"),
            "release_from_quarantine_document": (
                "member-3",
                "FR-02",
                "fr-02:release+mfa",
            ),
            "quarantine_document": ("member-3", "FR-02", "fr-02:quarantine+mfa"),
            "download_document": ("member-3", "FR-02", "fr-02:read"),
            "inherit_to_unit_document_link": ("member-3", "FR-02", "fr-02:inherit"),
            "override_document_link": ("member-3", "FR-02", "fr-02:override"),
            "resolve_conflict_document_link": ("member-3", "FR-02", "fr-02:resolve"),
            "detach_document_link": ("member-3", "FR-02", "fr-02:detach"),
            "create_project_parse_job": ("member-3", "FR-02", "fr-02:create"),
            "create_unit_parse_job": ("member-3", "FR-02", "fr-02:create"),
            "get_parse_job": ("member-3", "FR-02", "fr-02:read"),
            "retry_parse_job": ("member-3", "FR-02", "fr-02:retry"),
            "cancel_parse_job": ("member-3", "FR-02", "fr-02:cancel"),
            "list_document_derived_assets": ("member-3", "FR-02", "fr-02:read"),
            "get_derived_asset": ("member-3", "FR-02", "fr-02:read"),
            "list_replicas": ("member-3", "FR-02", "fr-02:read"),
            "list_manual_overrides": ("member-1", "PUBLIC", "gate:read"),
            "append_manual_override": (
                "member-1",
                "PUBLIC",
                "manual-override:append+mfa",
            ),
            "list_decision_baselines": (
                "member-6",
                "FR-06",
                "simulation:baseline:read",
            ),
            "freeze_decision_baseline": (
                "member-6",
                "FR-06",
                "simulation:baseline:freeze+mfa",
            ),
            "get_decision_baseline": (
                "member-6",
                "FR-06",
                "simulation:baseline:read",
            ),
            "list_candidate_search_spaces": (
                "member-6",
                "FR-06",
                "simulation:baseline:read",
            ),
            "create_candidate_search_space": (
                "member-6",
                "FR-06",
                "simulation:baseline:freeze+mfa",
            ),
            "get_candidate_search_space": (
                "member-6",
                "FR-06",
                "simulation:baseline:read",
            ),
            "list_scenario_sets": (
                "member-6",
                "FR-06",
                "simulation:baseline:read",
            ),
            "create_scenario_set": (
                "member-6",
                "FR-06",
                "simulation:baseline:freeze+mfa",
            ),
            "get_scenario_set": (
                "member-6",
                "FR-06",
                "simulation:baseline:read",
            ),
            "freeze_scenario_set": (
                "member-6",
                "FR-06",
                "simulation:baseline:freeze+mfa",
            ),
            "create_simulation_batch": (
                "member-6",
                "FR-07",
                "simulation:batch:run+mfa",
            ),
            "list_simulation_batches": (
                "member-6",
                "FR-07",
                "simulation:batch:read",
            ),
            "get_simulation_batch": (
                "member-6",
                "FR-07",
                "simulation:batch:read",
            ),
            "cancel_simulation_batch": (
                "member-6",
                "FR-07",
                "simulation:batch:run+mfa",
            ),
            "retry_simulation_batch": (
                "member-6",
                "FR-07",
                "simulation:batch:run+mfa",
            ),
            "list_simulation_batch_candidates": (
                "member-6",
                "FR-07",
                "simulation:batch:read",
            ),
            "list_simulation_batch_static_validations": (
                "member-6",
                "FR-07",
                "simulation:batch:read",
            ),
            "list_simulation_batch_scenario_outcomes": (
                "member-6",
                "FR-07",
                "simulation:batch:read",
            ),
            "list_simulation_batch_scenario_assessments": (
                "member-6",
                "FR-07",
                "simulation:batch:read",
            ),
            "create_optimization_run": (
                "member-6",
                "FR-08",
                "simulation:optimization:run+mfa",
            ),
            "list_optimization_runs": (
                "member-6",
                "FR-08",
                "simulation:optimization:run",
            ),
            "get_optimization_run": (
                "member-6",
                "FR-08",
                "simulation:optimization:run",
            ),
            "finalize_optimization_run": (
                "member-6",
                "FR-08",
                "simulation:optimization:run+mfa",
            ),
            "invalidate_optimization_run": (
                "member-6",
                "FR-08",
                "simulation:optimization:run+mfa",
            ),
            "list_optimization_stress_test_assessments": (
                "member-6",
                "FR-08",
                "simulation:optimization:run",
            ),
            "list_optimization_strategy_plans": (
                "member-6",
                "FR-08",
                "simulation:plan:publish",
            ),
            "list_optimization_merge_assessments": (
                "member-6",
                "FR-08",
                "simulation:optimization:run",
            ),
            "publish_strategy_plan": (
                "member-6",
                "FR-08",
                "simulation:plan:publish+mfa",
            ),
            "invalidate_strategy_plan": (
                "member-6",
                "FR-08",
                "simulation:plan:publish+mfa",
            ),
            "create_recommendation_eligibilitie": (
                "member-6",
                "FR-09a",
                "simulation:eligibility:assess+mfa",
            ),
            "list_recommendation_eligibilities": (
                "member-6",
                "FR-09a",
                "simulation:eligibility:assess",
            ),
            "get_recommendation_eligibilitie": (
                "member-6",
                "FR-09a",
                "simulation:eligibility:assess",
            ),
            "create_simulation_assessment_snapshot": (
                "member-6",
                "FR-09a",
                "simulation:snapshot:create+mfa",
            ),
            "list_simulation_assessment_snapshots": (
                "member-6",
                "FR-09a",
                "simulation:snapshot:create",
            ),
            "get_simulation_assessment_snapshot": (
                "member-6",
                "FR-09a",
                "simulation:snapshot:create",
            ),
            "download_simulation_assessment_snapshot": (
                "member-6",
                "FR-09a",
                "simulation:snapshot:create",
            ),
            "revoke_manual_override": (
                "member-1",
                "PUBLIC",
                "manual-override:append+mfa",
            ),
        }
        for spec in OPERATION_CATALOG:
            if spec.operation_id in contract_stubs.IMPLEMENTED_OPERATION_IDS:
                actual_owner[spec.operation_id] = (
                    spec.owner,
                    spec.fr,
                    spec.permission,
                )
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
                    operation.setdefault("x-schema-status", "FROZEN")
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
