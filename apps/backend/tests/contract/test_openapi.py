from __future__ import annotations

from fastapi.routing import APIRoute

from biaice.api.operation_catalog import OPERATION_CATALOG
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
FULLY_IMPLEMENTED_OWNERS = frozenset({"member-2", "member-3", "member-4", "member-5", "member-6"})
FULLY_IMPLEMENTED_OPERATION_IDS = frozenset(
    operation.operation_id
    for operation in OPERATION_CATALOG
    if operation.owner in FULLY_IMPLEMENTED_OWNERS
)
IMPLEMENTED_CATALOG_OPERATION_IDS = (
    FULLY_IMPLEMENTED_OPERATION_IDS | MEMBER7_IMPLEMENTED_OPERATION_IDS
)
MEMBER5_IMPLEMENTED_OPERATION_IDS = frozenset(
    operation.operation_id for operation in OPERATION_CATALOG if operation.owner == "member-5"
)


def operations(schema):
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                yield method.upper(), path, operation


def runtime_api_routes(routes):
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            yield from runtime_api_routes(original_router.routes)


def test_openapi_has_unique_operations_all_p0_groups_and_explicit_contract_only_flags() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    items = list(operations(schema))
    operation_ids = [item[2]["operationId"] for item in items]
    assert len(operation_ids) == len(set(operation_ids))
    assert {operation.operation_id for operation in OPERATION_CATALOG}.issubset(operation_ids)
    openapi_by_id = {item[2]["operationId"]: item[2] for item in items}
    for operation_id in FULLY_IMPLEMENTED_OPERATION_IDS:
        assert openapi_by_id[operation_id]["x-contract-only"] is False
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


def test_runtime_router_has_no_duplicate_method_path_or_operation_id() -> None:
    app = create_app(settings=Settings(environment="contract"))
    routes = list(runtime_api_routes(app.routes))
    method_paths = [
        (method, route.path) for route in routes for method in route.methods if method != "HEAD"
    ]
    operation_ids = [route.operation_id for route in routes]

    assert len(method_paths) == len(set(method_paths))
    assert len(operation_ids) == len(set(operation_ids))


def test_all_member5_implemented_schemas_are_explicitly_frozen() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    openapi_operations = {
        operation["operationId"]: operation for _, _, operation in operations(schema)
    }
    catalog_operations = {operation.operation_id: operation for operation in OPERATION_CATALOG}

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
