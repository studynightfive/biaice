from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.checks import (
    negative_data_rejection,
    positive_data_acceptance,
)

from biaice.api.model_lifecycle import MODEL_LIFECYCLE_OPERATION_IDS
from biaice.api.operation_catalog import OPERATION_CATALOG
from biaice.api.provider_management import PROVIDER_MANAGEMENT_OPERATION_IDS
from biaice.core.auth import Authenticator, IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.core.jobs import JobEvent, JobPort, JobState, JobView
from biaice.main import create_app

TENANT_ID = UUID("00000000-0000-4000-8000-000000000101")
DATA_DOMAIN_ID = UUID("00000000-0000-4000-8000-000000000102")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000103")
NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


class ContractAuthenticator(Authenticator):
    """Deterministic identity for in-process contract execution only."""

    def authenticate(self, token: str) -> IdentityContext:
        assert token == "schemathesis-contract-token"
        return IdentityContext(
            subject_id=ACTOR_ID,
            username="schemathesis-contract-user",
            display_name="Schemathesis Contract User",
            roles=frozenset(Role),
            scope=TenantScope(
                tenant_id=TENANT_ID,
                data_domain_id=DATA_DOMAIN_ID,
                all_projects=True,
                all_decision_units=True,
            ),
            mfa_verified=True,
            authenticated_at=NOW,
            session_id="schemathesis-contract-session",
        )


class ContractJobPort(JobPort):
    """Side-effect-free job port that lets success responses be schema-checked."""

    @staticmethod
    def _view(job_id: UUID, state: JobState) -> JobView:
        return JobView(
            job_id=job_id,
            job_type="contract.exercise",
            queue_name="governance",
            state=state,
            progress_percent=50,
            attempt=1,
            max_attempts=3,
            created_at=NOW,
            updated_at=NOW,
            status_url=f"/api/v1/jobs/{job_id}",
            events_url=f"/api/v1/jobs/{job_id}/events",
        )

    def get(self, *, scope: TenantScope, job_id: UUID) -> JobView:
        del scope
        return self._view(job_id, JobState.RUNNING)

    def cancel(
        self,
        *,
        scope: TenantScope,
        job_id: UUID,
        actor_id: UUID,
        idempotency_key: str,
    ) -> JobView:
        del scope, actor_id
        assert idempotency_key
        return self._view(job_id, JobState.CANCELLATION_REQUESTED)

    def retry(
        self,
        *,
        scope: TenantScope,
        job_id: UUID,
        actor_id: UUID,
        idempotency_key: str,
    ) -> JobView:
        del scope, actor_id
        assert idempotency_key
        return self._view(job_id, JobState.QUEUED)

    def events(self, *, scope: TenantScope, job_id: UUID, after: int = 0) -> Sequence[JobEvent]:
        del scope, job_id
        return (
            JobEvent(
                sequence=max(after + 1, 1),
                occurred_at=NOW,
                state=JobState.RUNNING,
                progress_percent=50,
            ),
        )


APP = create_app(
    settings=Settings(environment="contract"),
    authenticator=ContractAuthenticator(),
    job_port=ContractJobPort(),
)
OPENAPI = APP.openapi()

MEMBER7_IMPLEMENTED_OPERATION_IDS = frozenset(
    {
        "create_risk_acceptance",
        "list_risk_acceptances",
        "get_risk_acceptance",
        "revoke_risk_acceptance",
    }
)
MEMBER3_IMPLEMENTED_OPERATION_IDS = frozenset(
    {
        "create_project_document_upload_session",
        "create_unit_document_upload_session",
        "get_document_upload_session",
        "put_document_upload_chunk",
        "complete_document_upload_session",
        "cancel_document_upload_session",
        "list_project_documents",
        "list_unit_documents",
        "get_document",
        "review_document",
        "release_from_quarantine_document",
        "quarantine_document",
        "download_document",
        "inherit_to_unit_document_link",
        "override_document_link",
        "resolve_conflict_document_link",
        "detach_document_link",
        "create_project_parse_job",
        "create_unit_parse_job",
        "get_parse_job",
        "retry_parse_job",
        "cancel_parse_job",
        "list_document_derived_assets",
        "get_derived_asset",
        "list_replicas",
    }
)
FR05_IMPLEMENTED_OPERATION_IDS = frozenset(
    operation.operation_id for operation in OPERATION_CATALOG if operation.fr == "FR-05"
)
FR12_IMPLEMENTED_OPERATION_IDS = frozenset(
    operation.operation_id for operation in OPERATION_CATALOG if operation.fr == "FR-12"
)
IMPLEMENTED_CATALOG_OPERATION_IDS = (
    MEMBER7_IMPLEMENTED_OPERATION_IDS
    | MEMBER3_IMPLEMENTED_OPERATION_IDS
    | FR05_IMPLEMENTED_OPERATION_IDS
    | FR12_IMPLEMENTED_OPERATION_IDS
    | MODEL_LIFECYCLE_OPERATION_IDS
    | PROVIDER_MANAGEMENT_OPERATION_IDS
)

FR12_LIST_OPERATION_IDS = frozenset(
    operation.operation_id
    for operation in OPERATION_CATALOG
    if operation.fr == "FR-12" and operation.operation_id.startswith("list_")
)
MODEL_LIFECYCLE_LIST_OPERATION_IDS = frozenset(
    operation_id
    for operation_id in MODEL_LIFECYCLE_OPERATION_IDS
    if operation_id.startswith("list_")
)
PROVIDER_LIST_OPERATION_IDS = frozenset(
    {
        "list_ai_provider_configurations",
        "list_provider_invocations",
    }
)
SIGNED_CURSOR_LIST_OPERATION_IDS = (
    FR12_LIST_OPERATION_IDS
    | MODEL_LIFECYCLE_LIST_OPERATION_IDS
    | PROVIDER_LIST_OPERATION_IDS
)
FR12_MISSING_RESOURCE_OPERATION_IDS = frozenset(
    operation.operation_id
    for operation in OPERATION_CATALOG
    if operation.fr == "FR-12" and "{" in operation.path
)


def _operation_partitions() -> tuple[frozenset[str], frozenset[str]]:
    implemented: set[str] = set()
    contract_only: set[str] = set()
    for path_item in OPENAPI["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            destination = contract_only if operation.get("x-contract-only") is True else implemented
            destination.add(operation["operationId"])
    return frozenset(implemented), frozenset(contract_only)


IMPLEMENTED_OPERATION_IDS, CONTRACT_ONLY_OPERATION_IDS = _operation_partitions()
IMPLEMENTED_SCHEMA = schemathesis.openapi.from_asgi("/api/openapi.json", APP).include(
    operation_id=sorted(IMPLEMENTED_OPERATION_IDS)
)

# These handlers are deliberately fail-closed M0 foundation endpoints. They are
# still executed and response-contract checked; only Schemathesis' generic
# "no 5xx" check is waived for the exact documented status.
EXPECTED_FOUNDATION_UNAVAILABLE: dict[str, frozenset[int]] = {
    "assess_stage_gate": frozenset({503}),
    "list_manual_overrides": frozenset({501}),
    "append_manual_override": frozenset({501}),
    "revoke_manual_override": frozenset({501}),
    "set_ai_provider_credential": frozenset({503}),
    "test_ai_provider_connection": frozenset({503}),
    "activate_ai_provider_configuration": frozenset({503}),
}

# Cross-field business rules (valid_until > valid_from) cannot be expressed in
# the OpenAPI schema, and Schemathesis' UUID path examples can be rejected by
# FastAPI's stricter parser. The documented 422 is still the fail-closed
# answer; only the generic "positive data must be accepted" check is waived
# for these operations. Positive and negative paths are covered by explicit
# contract tests.
EXPECTED_BUSINESS_RULE_422: frozenset[str] = frozenset(
    {
        "create_risk_acceptance",
        "create_project_document_upload_session",
        "create_unit_document_upload_session",
        "put_document_upload_chunk",
        "complete_document_upload_session",
        "cancel_document_upload_session",
        "review_document",
        "release_from_quarantine_document",
        "quarantine_document",
        "create_project_parse_job",
        "create_unit_parse_job",
        "retry_parse_job",
        "cancel_parse_job",
        "inherit_to_unit_document_link",
        "override_document_link",
        "resolve_conflict_document_link",
        "detach_document_link",
        "create_competitor",
        "update_competitor_draft",
        "create_market_prior",
        "create_unknown_entrant_profile",
        "create_dataset",
        "create_feature_schema",
        "create_evaluation_protocol",
        "create_monitoring_snapshot",
        "create_ai_provider_catalog_version",
        "create_ai_provider_configuration",
        "publish_ai_provider_catalog_version",
        "revoke_ai_provider_catalog_version",
        "create_ai_provider_configuration_successor",
        "revoke_ai_provider_credential",
        "suspend_ai_provider_configuration",
        "revoke_ai_provider_configuration",
    }
)
EXPECTED_ETAG_PRECONDITION: frozenset[str] = frozenset(
    {"update_competitor_draft", "update_ai_provider_configuration"}
)
EXPECTED_MISSING_RESOURCE: frozenset[str] = (
    frozenset(
        {
            "get_document_upload_session",
            "put_document_upload_chunk",
            "complete_document_upload_session",
            "cancel_document_upload_session",
            "get_document",
            "review_document",
            "release_from_quarantine_document",
            "quarantine_document",
            "download_document",
            "create_project_parse_job",
            "create_unit_parse_job",
            "get_parse_job",
            "retry_parse_job",
            "cancel_parse_job",
            "list_document_derived_assets",
            "get_derived_asset",
            "inherit_to_unit_document_link",
            "override_document_link",
            "resolve_conflict_document_link",
            "detach_document_link",
            "get_dataset",
            "publish_dataset",
            "get_feature_schema",
            "publish_feature_schema",
            "create_model_artifact",
            "get_model_artifact",
            "publish_model_artifact",
            "create_evaluation_protocol",
            "get_evaluation_protocol",
            "publish_evaluation_protocol",
            "create_calibration_artifact",
            "get_calibration_artifact",
            "create_monitoring_snapshot",
            "get_monitoring_snapshot",
            "create_model_incident",
            "get_model_incident",
            "create_rollback_event",
            "get_rollback_event",
            "create_model_approval",
            "decide_model_approval",
            "create_model_deployment",
            "activate_model_deployment",
            "rollback_model_deployment",
            "get_competitor",
            "update_competitor_draft",
            "archive_competitor",
            "list_competitor_sources",
            "create_competitor_source",
            "get_competitor_source",
            "review_competitor_source",
            "quarantine_competitor_source",
            "list_competitor_profiles",
            "build_competitor_profile",
            "get_competitor_profile",
            "publish_competitor_profile",
            "get_market_prior",
            "review_market_prior",
            "publish_market_prior",
            "get_unknown_entrant_profile",
            "publish_unknown_entrant_profile",
            "get_subject_deduplication_run",
            "get_ai_provider_catalog_version",
            "publish_ai_provider_catalog_version",
            "revoke_ai_provider_catalog_version",
            "create_ai_provider_configuration",
            "get_ai_provider_configuration",
            "update_ai_provider_configuration",
            "create_ai_provider_configuration_successor",
            "revoke_ai_provider_credential",
            "suspend_ai_provider_configuration",
            "revoke_ai_provider_configuration",
            "get_provider_invocation",
        }
    )
    | FR12_MISSING_RESOURCE_OPERATION_IDS
)


def test_schemathesis_version_and_openapi_partition_are_explicit() -> None:
    assert schemathesis.__version__ == "4.24.3"
    assert IMPLEMENTED_OPERATION_IDS
    assert CONTRACT_ONLY_OPERATION_IDS
    assert IMPLEMENTED_OPERATION_IDS.isdisjoint(CONTRACT_ONLY_OPERATION_IDS)
    implemented_in_catalog = IMPLEMENTED_OPERATION_IDS & frozenset(
        operation.operation_id for operation in OPERATION_CATALOG
    )
    assert implemented_in_catalog == IMPLEMENTED_CATALOG_OPERATION_IDS
    assert len(CONTRACT_ONLY_OPERATION_IDS) == (
        len(OPERATION_CATALOG) - len(IMPLEMENTED_CATALOG_OPERATION_IDS)
    )


@IMPLEMENTED_SCHEMA.parametrize()
@settings(
    max_examples=8,
    deadline=None,
    derandomize=True,
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.filter_too_much),
)
def test_implemented_operations_conform_to_openapi(case: schemathesis.Case) -> None:
    """Execute every non-contract-only operation through Schemathesis' ASGI transport."""

    headers = {
        "Authorization": "Bearer schemathesis-contract-token",
        "Idempotency-Key": "schemathesis-contract-idempotency-key",
    }
    response = case.call(headers=headers)
    operation_id = case.operation.definition.raw["operationId"]
    allowed_server_errors = EXPECTED_FOUNDATION_UNAVAILABLE.get(operation_id, frozenset())

    if response.status_code >= 500:
        assert response.status_code in allowed_server_errors, (
            operation_id,
            response.status_code,
            response.text,
        )

    excluded_checks = []
    if response.status_code in allowed_server_errors:
        excluded_checks.append(schemathesis.checks.not_a_server_error)
    if response.status_code == 422 and operation_id in EXPECTED_BUSINESS_RULE_422:
        excluded_checks.append(positive_data_acceptance)
    if response.status_code == 400 and operation_id in SIGNED_CURSOR_LIST_OPERATION_IDS:
        # Cursor is an HMAC-signed capability. Arbitrary schema-valid strings
        # must fail closed; explicit domain tests cover valid and tampered cursors.
        excluded_checks.append(positive_data_acceptance)
    if response.status_code in {412, 428} and operation_id in EXPECTED_ETAG_PRECONDITION:
        excluded_checks.extend((positive_data_acceptance, negative_data_rejection))
    if (
        response.status_code in {404, 409, 410}
        and operation_id in EXPECTED_MISSING_RESOURCE | EXPECTED_BUSINESS_RULE_422
    ):
        excluded_checks.append(positive_data_acceptance)
    case.validate_response(
        response,
        headers=headers,
        excluded_checks=excluded_checks,
    )
