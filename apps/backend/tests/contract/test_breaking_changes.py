from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "scripts" / "contracts" / "check_breaking_changes.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_breaking_changes", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


def _document(operation: dict, *, security_schemes: dict | None = None) -> dict:
    return {
        "openapi": "3.1.0",
        "paths": {"/widgets": {"post": operation}},
        "components": {"schemas": {}, "securitySchemes": security_schemes or {}},
    }


def _operation() -> dict:
    return {
        "operationId": "createWidget",
        "parameters": [],
        "responses": {
            "200": {
                "description": "Created widget",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"id": {"type": "string"}},
                            "required": ["id"],
                            "additionalProperties": False,
                        }
                    }
                },
            }
        },
    }


def test_adding_required_parameter_breaks_but_making_it_optional_does_not() -> None:
    old_operation = _operation()
    old_operation["parameters"] = [
        {
            "in": "query",
            "name": "limit",
            "required": False,
            "schema": {"type": "integer"},
        }
    ]
    new_operation = copy.deepcopy(old_operation)
    new_operation["parameters"][0]["required"] = True

    failures = checker.find_breaking_changes(
        _document(old_operation), _document(new_operation)
    )
    assert any("new required parameters [('query', 'limit')]" in item for item in failures)

    reverse_failures = checker.find_breaking_changes(
        _document(new_operation), _document(old_operation)
    )
    assert not any("required parameters" in item for item in reverse_failures)


def test_request_schema_cannot_add_a_required_property() -> None:
    old_operation = _operation()
    old_operation["requestBody"] = {
        "required": False,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                }
            }
        },
    }
    new_operation = copy.deepcopy(old_operation)
    new_operation["requestBody"]["content"]["application/json"]["schema"][
        "required"
    ] = ["query"]

    failures = checker.find_breaking_changes(
        _document(old_operation), _document(new_operation)
    )
    assert any("new required request properties ['query']" in item for item in failures)


def test_response_schema_cannot_remove_a_property_or_expand_an_enum() -> None:
    old_operation = _operation()
    response_schema = old_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    response_schema["properties"]["status"] = {
        "type": "string",
        "enum": ["ready"],
    }
    response_schema["required"].append("status")

    new_operation = copy.deepcopy(old_operation)
    new_schema = new_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    del new_schema["properties"]["id"]
    new_schema["required"].remove("id")
    new_schema["properties"]["status"]["enum"].append("pending")

    failures = checker.find_breaking_changes(
        _document(old_operation), _document(new_operation)
    )
    assert any("removed response properties ['id']" in item for item in failures)
    assert any("incompatible response enum" in item for item in failures)


def test_response_status_and_media_type_removal_break() -> None:
    old_operation = _operation()
    new_operation = copy.deepcopy(old_operation)
    new_operation["responses"] = {
        "201": {
            "description": "Created widget",
            "content": {"application/problem+json": {"schema": {"type": "object"}}},
        }
    }

    failures = checker.find_breaking_changes(
        _document(old_operation), _document(new_operation)
    )
    assert "createWidget: removed success responses ['200']" in failures

    media_operation = copy.deepcopy(old_operation)
    media_operation["responses"]["200"]["content"] = {}
    media_failures = checker.find_breaking_changes(
        _document(old_operation), _document(media_operation)
    )
    assert any("removed media type application/json" in item for item in media_failures)


def test_effective_security_or_scheme_changes_break() -> None:
    scheme = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    old_operation = _operation()
    old_operation["security"] = [{"bearerAuth": []}]
    new_operation = copy.deepcopy(old_operation)
    new_operation["security"] = []

    failures = checker.find_breaking_changes(
        _document(old_operation, security_schemes={"bearerAuth": scheme}),
        _document(new_operation, security_schemes={"bearerAuth": scheme}),
    )
    assert "createWidget: changed effective security requirements" in failures

    changed_scheme = {**scheme, "scheme": "basic"}
    scheme_failures = checker.find_breaking_changes(
        _document(old_operation, security_schemes={"bearerAuth": scheme}),
        _document(old_operation, security_schemes={"bearerAuth": changed_scheme}),
    )
    assert "changed security scheme: bearerAuth" in scheme_failures


def test_contract_only_stub_graduation_is_not_a_breaking_change() -> None:
    old_operation = _operation()
    old_operation["x-contract-only"] = True
    old_operation["x-schema-status"] = "STUB_FIELDS_PENDING_OWNER_FREEZE"
    old_operation["responses"]["200"]["content"]["application/json"]["schema"] = {
        "type": "object",
        "properties": {
            "contract_only": {"type": "boolean"},
            "operation_id": {"type": "string"},
            "owner": {"type": "string"},
            "schema_status": {"type": "string"},
        },
        "required": ["operation_id", "owner", "schema_status"],
        "additionalProperties": True,
    }
    old_operation["requestBody"] = {
        "required": False,
        "content": {"application/json": {"schema": {}}},
    }

    new_operation = _operation()
    new_operation["requestBody"] = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "rationale": {"type": "string"},
                        "risk": {"type": "string"},
                    },
                    "required": ["rationale", "risk"],
                    "additionalProperties": False,
                }
            }
        },
    }

    failures = checker.find_breaking_changes(
        _document(old_operation), _document(new_operation)
    )
    assert failures == []

    # Still-stub updates remain subject to compatibility checks.
    still_stub = copy.deepcopy(old_operation)
    stub_schema = still_stub["responses"]["200"]["content"]["application/json"]["schema"]
    del stub_schema["properties"]["owner"]
    stub_schema["required"].remove("owner")
    stub_failures = checker.find_breaking_changes(
        _document(old_operation), _document(still_stub)
    )
    assert any("removed response properties ['owner']" in item for item in stub_failures)


def test_missing_baseline_fails_closed_unless_initial_freeze_is_explicit(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(checker, "load_baseline", lambda _ref: None)

    assert checker.main(["origin/main"]) == 2
    assert "baseline is unavailable" in capsys.readouterr().out

    assert checker.main(["origin/main", "--allow-missing-baseline"]) == 0
    assert "explicitly allowed" in capsys.readouterr().out
