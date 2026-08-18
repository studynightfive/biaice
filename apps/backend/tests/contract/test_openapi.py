from __future__ import annotations

from biaice.api.model_lifecycle import MODEL_LIFECYCLE_OPERATION_IDS
from biaice.api.operation_catalog import OPERATION_CATALOG
from biaice.api.provider_management import PROVIDER_MANAGEMENT_OPERATION_IDS
from biaice.core.config import Settings
from biaice.core.outbox import EVENT_CATALOG
from biaice.main import create_app

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
MEMBER6_IMPLEMENTED_OPERATION_IDS = (
    frozenset(
        {
        "list_decision_baselines",
        "freeze_decision_baseline",
        "get_decision_baseline",
        "list_candidate_search_spaces",
        "create_candidate_search_space",
        "get_candidate_search_space",
        "list_scenario_sets",
        "create_scenario_set",
        "get_scenario_set",
        "freeze_scenario_set",
        "create_simulation_batch",
        "list_simulation_batches",
        "get_simulation_batch",
        "cancel_simulation_batch",
        "retry_simulation_batch",
        "list_simulation_batch_candidates",
        "list_simulation_batch_static_validations",
        "list_simulation_batch_scenario_outcomes",
        "list_simulation_batch_scenario_assessments",
        "create_optimization_run",
        "list_optimization_runs",
        "get_optimization_run",
        "finalize_optimization_run",
        "invalidate_optimization_run",
        "list_optimization_stress_test_assessments",
        "list_optimization_strategy_plans",
        "list_optimization_merge_assessments",
        "publish_strategy_plan",
        "invalidate_strategy_plan",
        "create_recommendation_eligibilitie",
        "list_recommendation_eligibilities",
        "get_recommendation_eligibilitie",
        "create_simulation_assessment_snapshot",
        "list_simulation_assessment_snapshots",
        "get_simulation_assessment_snapshot",
        "download_simulation_assessment_snapshot",
        }
    )
)
IMPLEMENTED_CATALOG_OPERATION_IDS = (
    MEMBER7_IMPLEMENTED_OPERATION_IDS
    | MEMBER3_IMPLEMENTED_OPERATION_IDS
    | FR05_IMPLEMENTED_OPERATION_IDS
    | FR12_IMPLEMENTED_OPERATION_IDS
    | MODEL_LIFECYCLE_OPERATION_IDS
    | PROVIDER_MANAGEMENT_OPERATION_IDS
    | MEMBER6_IMPLEMENTED_OPERATION_IDS
)
MEMBER5_IMPLEMENTED_OPERATION_IDS = (
    FR05_IMPLEMENTED_OPERATION_IDS
    | FR12_IMPLEMENTED_OPERATION_IDS
    | MODEL_LIFECYCLE_OPERATION_IDS
    | PROVIDER_MANAGEMENT_OPERATION_IDS
)


def operations(schema):
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                yield method.upper(), path, operation


def test_openapi_has_unique_operations_all_p0_groups_and_explicit_contract_only_flags() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    items = list(operations(schema))
    operation_ids = [item[2]["operationId"] for item in items]
    assert len(operation_ids) == len(set(operation_ids))
    implemented = [
        operation
        for operation in OPERATION_CATALOG
        if operation.operation_id in IMPLEMENTED_CATALOG_OPERATION_IDS
    ]
    assert len([item for item in items if item[2].get("x-contract-only")]) == (
        len(OPERATION_CATALOG) - len(implemented)
    )
    covered = {item[2]["x-fr"] for item in items}
    assert {
        "FR-01",
        "FR-02",
        "FR-03",
        "FR-04",
        "FR-05",
        "FR-06",
        "FR-07",
        "FR-08",
        "FR-09a",
        "FR-09b",
        "FR-10",
        "FR-11",
        "FR-12",
        "FR-13",
    }.issubset(covered)


def test_all_member5_implemented_schemas_are_explicitly_frozen() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    openapi_operations = {
        operation["operationId"]: operation for _, _, operation in operations(schema)
    }
    catalog_operations = {
        operation.operation_id: operation for operation in OPERATION_CATALOG
    }

    assert MEMBER5_IMPLEMENTED_OPERATION_IDS == {
        operation_id
        for operation_id, operation in catalog_operations.items()
        if operation.owner == "member-5"
    }
    for operation_id in MEMBER5_IMPLEMENTED_OPERATION_IDS:
        assert catalog_operations[operation_id].schema_status == "FROZEN"
        assert openapi_operations[operation_id]["x-schema-status"] == "FROZEN"


def test_error_responses_are_documented_as_problem_json() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    for _, _, operation in operations(schema):
        for code, response in operation.get("responses", {}).items():
            if str(code).startswith(("4", "5")) and response.get("content"):
                assert "application/problem+json" in response["content"], (
                    operation["operationId"],
                    code,
                )


def test_validation_response_description_is_python_minor_independent() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    descriptions = {
        response["description"]
        for _, _, operation in operations(schema)
        for code, response in operation.get("responses", {}).items()
        if str(code) == "422"
    }
    assert descriptions == {"Unprocessable Content"}


def test_cross_member_event_catalog_marks_unfrozen_payloads_contract_only() -> None:
    assert EVENT_CATALOG["rules.scope_assessment_published.v1"]["owner"] == "member-2"
    assert EVENT_CATALOG["documents.replica_deletion_receipt_produced.v1"]["owner"] == "member-3"
    assert (
        EVENT_CATALOG["model_governance.provider_replica_deletion_receipt_produced.v1"]["owner"]
        == "member-5"
    )
    assert EVENT_CATALOG["governance.deletion.completed.v1"]["owner"] == "member-1"
    assert EVENT_CATALOG["rules.scope_assessment_published.v1"]["contract_only"] is True
    assert EVENT_CATALOG["governance.deletion.completed.v1"]["contract_only"] is False
