"""Reject backward-incompatible OpenAPI changes against a Git baseline.

This intentionally implements a small, dependency-free compatibility gate. It is
not a complete OpenAPI diff engine, but it covers the contract surfaces relied on
by generated clients: operations, parameters, request/response schemas and
authentication requirements.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = "packages/contracts/openapi.generated.json"
HTTP_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)

JsonObject = dict[str, Any]
Direction = Literal["request", "response"]
Operation = tuple[str, str, JsonObject, JsonObject]


def operation_map(schema: JsonObject) -> dict[str, Operation]:
    """Index operations while retaining their Path Item for inherited parameters."""

    result: dict[str, Operation] = {}
    for path, path_item in schema.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str):
                result[operation_id] = (method.upper(), path, operation, path_item)
    return result


def _json_pointer(document: JsonObject, ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValueError(f"external reference cannot be resolved: {ref}")
    value: Any = document
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or token not in value:
            raise ValueError(f"unresolvable local reference: {ref}")
        value = value[token]
    return value


def _resolve(document: JsonObject, value: Any) -> Any:
    """Resolve local references and preserve any JSON Schema sibling keywords."""

    seen: set[str] = set()
    while isinstance(value, dict) and isinstance(value.get("$ref"), str):
        ref = value["$ref"]
        if not ref.startswith("#/") or ref in seen:
            break
        seen.add(ref)
        target = _json_pointer(document, ref)
        if not isinstance(target, dict):
            return target
        siblings = {key: item for key, item in value.items() if key != "$ref"}
        if siblings:
            value = {**target, **siblings}
        else:
            value = target
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _type_set(schema: JsonObject) -> frozenset[str] | None:
    value = schema.get("type")
    if isinstance(value, str):
        return frozenset({value})
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return frozenset(value)
    return None


def _accepts_type(accepted: frozenset[str], candidate: str) -> bool:
    return candidate in accepted or (candidate == "integer" and "number" in accepted)


def _type_change_breaks(
    old_types: frozenset[str] | None,
    new_types: frozenset[str] | None,
    direction: Direction,
) -> bool:
    if direction == "request":
        if old_types is None:
            return new_types is not None
        if new_types is None:
            return False
        return any(not _accepts_type(new_types, item) for item in old_types)
    if old_types is None:
        return False
    if new_types is None:
        return True
    return any(not _accepts_type(old_types, item) for item in new_types)


def _visible_properties(
    schema: JsonObject, document: JsonObject, direction: Direction
) -> dict[str, Any]:
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}
    result: dict[str, Any] = {}
    for name, property_schema in properties.items():
        resolved = _resolve(document, property_schema)
        if (
            direction == "request"
            and isinstance(resolved, dict)
            and resolved.get("readOnly") is True
        ):
            continue
        if (
            direction == "response"
            and isinstance(resolved, dict)
            and resolved.get("writeOnly") is True
        ):
            continue
        result[name] = property_schema
    return result


def _additional_properties_allowed(schema: JsonObject) -> bool:
    return schema.get("additionalProperties", True) is not False


def _schema_breakages(
    old_schema: Any,
    new_schema: Any,
    old_document: JsonObject,
    new_document: JsonObject,
    direction: Direction,
    location: str,
    failures: list[str],
    seen: set[tuple[int, int, Direction]],
) -> None:
    if old_schema is None:
        return
    if new_schema is None:
        failures.append(f"{location}: removed {direction} schema")
        return

    unresolved_old = old_schema
    unresolved_new = new_schema
    old_schema = _resolve(old_document, old_schema)
    new_schema = _resolve(new_document, new_schema)
    if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
        if _canonical(old_schema) != _canonical(new_schema):
            failures.append(f"{location}: changed {direction} schema")
        return

    pair = (id(old_schema), id(new_schema), direction)
    if pair in seen:
        return
    seen.add(pair)

    old_ref = unresolved_old.get("$ref") if isinstance(unresolved_old, dict) else None
    new_ref = unresolved_new.get("$ref") if isinstance(unresolved_new, dict) else None
    if isinstance(old_ref, str) and not old_ref.startswith("#/") and old_ref != new_ref:
        failures.append(f"{location}: changed external schema reference")
        return

    old_types = _type_set(old_schema)
    new_types = _type_set(new_schema)
    if _type_change_breaks(old_types, new_types, direction):
        failures.append(
            f"{location}: incompatible {direction} type "
            f"{sorted(old_types) if old_types else 'any'} -> "
            f"{sorted(new_types) if new_types else 'any'}"
        )

    old_format = old_schema.get("format")
    new_format = new_schema.get("format")
    format_breaks = (
        direction == "request" and new_format is not None and new_format != old_format
    ) or (
        direction == "response" and old_format is not None and new_format != old_format
    )
    if format_breaks:
        failures.append(
            f"{location}: incompatible {direction} format {old_format!r} -> {new_format!r}"
        )

    old_enum = old_schema.get("enum")
    new_enum = new_schema.get("enum")
    if isinstance(old_enum, list) or isinstance(new_enum, list):
        old_values = (
            {_canonical(item) for item in old_enum}
            if isinstance(old_enum, list)
            else None
        )
        new_values = (
            {_canonical(item) for item in new_enum}
            if isinstance(new_enum, list)
            else None
        )
        enum_breaks = (
            direction == "request"
            and new_values is not None
            and (old_values is None or not old_values.issubset(new_values))
        ) or (
            direction == "response"
            and old_values is not None
            and (new_values is None or not new_values.issubset(old_values))
        )
        if enum_breaks:
            failures.append(f"{location}: incompatible {direction} enum")

    old_const = old_schema.get("const")
    new_const = new_schema.get("const")
    if ("const" in old_schema or "const" in new_schema) and old_const != new_const:
        failures.append(f"{location}: changed {direction} const value")

    for keyword in ("oneOf", "anyOf", "allOf"):
        old_branches = old_schema.get(keyword)
        new_branches = new_schema.get(keyword)
        if old_branches is None and new_branches is None:
            continue
        if not isinstance(old_branches, list) or not isinstance(new_branches, list):
            failures.append(f"{location}: changed {direction} {keyword} alternatives")
            continue
        if len(old_branches) != len(new_branches):
            failures.append(
                f"{location}: changed {direction} {keyword} alternative count"
            )
            continue
        for index, (old_branch, new_branch) in enumerate(
            zip(old_branches, new_branches)
        ):
            _schema_breakages(
                old_branch,
                new_branch,
                old_document,
                new_document,
                direction,
                f"{location}.{keyword}[{index}]",
                failures,
                seen,
            )

    old_properties = _visible_properties(old_schema, old_document, direction)
    new_properties = _visible_properties(new_schema, new_document, direction)
    removed_properties = set(old_properties) - set(new_properties)
    if removed_properties:
        failures.append(
            f"{location}: removed {direction} properties {sorted(removed_properties)}"
        )

    old_required = set(old_schema.get("required", [])) & set(old_properties)
    new_required = set(new_schema.get("required", [])) & set(new_properties)
    if direction == "request":
        incompatible_required = new_required - old_required
        required_message = "new required request properties"
    else:
        incompatible_required = old_required - new_required
        required_message = "response properties no longer required"
    if incompatible_required:
        failures.append(
            f"{location}: {required_message} {sorted(incompatible_required)}"
        )

    for property_name in sorted(set(old_properties) & set(new_properties)):
        _schema_breakages(
            old_properties[property_name],
            new_properties[property_name],
            old_document,
            new_document,
            direction,
            f"{location}.{property_name}",
            failures,
            seen,
        )

    old_additional = _additional_properties_allowed(old_schema)
    new_additional = _additional_properties_allowed(new_schema)
    additional_breaks = (
        direction == "request" and old_additional and not new_additional
    ) or (direction == "response" and not old_additional and new_additional)
    if additional_breaks:
        failures.append(f"{location}: incompatible {direction} additionalProperties")
    old_additional_schema = old_schema.get("additionalProperties")
    new_additional_schema = new_schema.get("additionalProperties")
    if isinstance(old_additional_schema, dict) and isinstance(
        new_additional_schema, dict
    ):
        _schema_breakages(
            old_additional_schema,
            new_additional_schema,
            old_document,
            new_document,
            direction,
            f"{location}.*",
            failures,
            seen,
        )

    if "items" in old_schema:
        _schema_breakages(
            old_schema.get("items"),
            new_schema.get("items"),
            old_document,
            new_document,
            direction,
            f"{location}[]",
            failures,
            seen,
        )


def _parameter_map(
    document: JsonObject, path_item: JsonObject, operation: JsonObject
) -> dict[tuple[str, str], JsonObject]:
    result: dict[tuple[str, str], JsonObject] = {}
    for parameter in [
        *path_item.get("parameters", []),
        *operation.get("parameters", []),
    ]:
        parameter = _resolve(document, parameter)
        if not isinstance(parameter, dict):
            continue
        location = parameter.get("in")
        name = parameter.get("name")
        if isinstance(location, str) and isinstance(name, str):
            result[(location, name)] = parameter
    return result


def _effective_security(document: JsonObject, operation: JsonObject) -> Any:
    return (
        operation["security"]
        if "security" in operation
        else document.get("security", [])
    )


def _normalize_security(
    value: Any,
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]:
    if not isinstance(value, list):
        return ()
    alternatives: list[tuple[tuple[str, tuple[str, ...]], ...]] = []
    for alternative in value:
        if not isinstance(alternative, dict):
            continue
        requirement = tuple(
            sorted(
                (
                    str(scheme),
                    tuple(sorted(str(scope) for scope in scopes))
                    if isinstance(scopes, list)
                    else (),
                )
                for scheme, scopes in alternative.items()
            )
        )
        alternatives.append(requirement)
    return tuple(sorted(alternatives))


def _compare_request_body(
    operation_id: str,
    old_operation: JsonObject,
    new_operation: JsonObject,
    old_document: JsonObject,
    new_document: JsonObject,
    failures: list[str],
) -> None:
    old_body = _resolve(old_document, old_operation.get("requestBody"))
    new_body = _resolve(new_document, new_operation.get("requestBody"))
    if old_body is None:
        if isinstance(new_body, dict) and new_body.get("required") is True:
            failures.append(f"{operation_id}: added required request body")
        return
    if not isinstance(old_body, dict) or not isinstance(new_body, dict):
        failures.append(f"{operation_id}: removed request body")
        return
    if old_body.get("required") is not True and new_body.get("required") is True:
        failures.append(f"{operation_id}: request body became required")

    old_content = old_body.get("content", {})
    new_content = new_body.get("content", {})
    if not isinstance(old_content, dict) or not isinstance(new_content, dict):
        failures.append(f"{operation_id}: removed request body content")
        return
    for media_type, old_media in old_content.items():
        new_media = new_content.get(media_type)
        if not isinstance(old_media, dict) or not isinstance(new_media, dict):
            failures.append(f"{operation_id}: removed request media type {media_type}")
            continue
        _schema_breakages(
            old_media.get("schema"),
            new_media.get("schema"),
            old_document,
            new_document,
            "request",
            f"{operation_id} request {media_type}",
            failures,
            set(),
        )


def _compare_response(
    operation_id: str,
    status: str,
    old_response: Any,
    new_response: Any,
    old_document: JsonObject,
    new_document: JsonObject,
    failures: list[str],
) -> None:
    old_response = _resolve(old_document, old_response)
    new_response = _resolve(new_document, new_response)
    if not isinstance(old_response, dict) or not isinstance(new_response, dict):
        return
    old_content = old_response.get("content", {})
    new_content = new_response.get("content", {})
    if isinstance(old_content, dict) and isinstance(new_content, dict):
        for media_type, old_media in old_content.items():
            new_media = new_content.get(media_type)
            if not isinstance(old_media, dict) or not isinstance(new_media, dict):
                failures.append(
                    f"{operation_id} response {status}: removed media type {media_type}"
                )
                continue
            _schema_breakages(
                old_media.get("schema"),
                new_media.get("schema"),
                old_document,
                new_document,
                "response",
                f"{operation_id} response {status} {media_type}",
                failures,
                set(),
            )
    elif old_content:
        failures.append(f"{operation_id} response {status}: removed response content")

    old_headers = old_response.get("headers", {})
    new_headers = new_response.get("headers", {})
    if not isinstance(old_headers, dict) or not isinstance(new_headers, dict):
        return
    normalized_new_headers = {
        name.lower(): value for name, value in new_headers.items()
    }
    for header_name, old_header in old_headers.items():
        new_header = normalized_new_headers.get(header_name.lower())
        if new_header is None:
            failures.append(
                f"{operation_id} response {status}: removed header {header_name}"
            )
            continue
        old_header = _resolve(old_document, old_header)
        new_header = _resolve(new_document, new_header)
        if isinstance(old_header, dict) and isinstance(new_header, dict):
            _schema_breakages(
                old_header.get("schema"),
                new_header.get("schema"),
                old_document,
                new_document,
                "response",
                f"{operation_id} response {status} header {header_name}",
                failures,
                set(),
            )


def find_breaking_changes(baseline: JsonObject, current: JsonObject) -> list[str]:
    """Return deterministic descriptions of detected compatibility breaks."""

    failures: list[str] = []
    old_schemas = baseline.get("components", {}).get("schemas", {})
    new_schemas = current.get("components", {}).get("schemas", {})
    if isinstance(old_schemas, dict) and isinstance(new_schemas, dict):
        removed_schemas = set(old_schemas) - set(new_schemas)
        if removed_schemas:
            failures.append(f"removed component schemas: {sorted(removed_schemas)}")

    old_security_schemes = baseline.get("components", {}).get("securitySchemes", {})
    new_security_schemes = current.get("components", {}).get("securitySchemes", {})
    if isinstance(old_security_schemes, dict) and isinstance(
        new_security_schemes, dict
    ):
        for scheme_name, old_scheme in old_security_schemes.items():
            if scheme_name not in new_security_schemes:
                failures.append(f"removed security scheme: {scheme_name}")
            elif _canonical(old_scheme) != _canonical(
                new_security_schemes[scheme_name]
            ):
                failures.append(f"changed security scheme: {scheme_name}")

    old_operations = operation_map(baseline)
    new_operations = operation_map(current)
    for operation_id, (
        old_method,
        old_path,
        old_operation,
        old_path_item,
    ) in old_operations.items():
        candidate = new_operations.get(operation_id)
        if candidate is None:
            failures.append(f"removed operationId: {operation_id}")
            continue
        new_method, new_path, new_operation, new_path_item = candidate
        if (old_method, old_path) != (new_method, new_path):
            failures.append(
                f"moved operationId {operation_id}: "
                f"{old_method} {old_path} -> {new_method} {new_path}"
            )

        # Graduating a blocked contract-only stub into an implemented schema is
        # the intentional owner field-freeze path (see packages/contracts/README.md).
        # Stub placeholder fields must not trap that freeze as a client break.
        if (
            old_operation.get("x-contract-only") is True
            and new_operation.get("x-contract-only") is not True
        ):
            continue

        old_parameters = _parameter_map(baseline, old_path_item, old_operation)
        new_parameters = _parameter_map(current, new_path_item, new_operation)
        removed_parameters = set(old_parameters) - set(new_parameters)
        if removed_parameters:
            failures.append(
                f"{operation_id}: removed parameters {sorted(removed_parameters)}"
            )
        old_required = {
            key
            for key, parameter in old_parameters.items()
            if parameter.get("required") is True
        }
        new_required = {
            key
            for key, parameter in new_parameters.items()
            if parameter.get("required") is True
        }
        newly_required = new_required - old_required
        if newly_required:
            failures.append(
                f"{operation_id}: new required parameters {sorted(newly_required)}"
            )
        for parameter_key in sorted(set(old_parameters) & set(new_parameters)):
            old_parameter = old_parameters[parameter_key]
            new_parameter = new_parameters[parameter_key]
            _schema_breakages(
                old_parameter.get("schema"),
                new_parameter.get("schema"),
                baseline,
                current,
                "request",
                f"{operation_id} parameter {parameter_key}",
                failures,
                set(),
            )

        old_security = _normalize_security(_effective_security(baseline, old_operation))
        new_security = _normalize_security(_effective_security(current, new_operation))
        if old_security != new_security:
            failures.append(f"{operation_id}: changed effective security requirements")

        _compare_request_body(
            operation_id,
            old_operation,
            new_operation,
            baseline,
            current,
            failures,
        )

        old_responses = old_operation.get("responses", {})
        new_responses = new_operation.get("responses", {})
        if not isinstance(old_responses, dict) or not isinstance(new_responses, dict):
            continue
        old_success = {str(code) for code in old_responses if str(code).startswith("2")}
        new_success = {str(code) for code in new_responses if str(code).startswith("2")}
        removed_success = old_success - new_success
        if removed_success:
            failures.append(
                f"{operation_id}: removed success responses {sorted(removed_success)}"
            )
        normalized_new_responses = {
            str(code): response for code, response in new_responses.items()
        }
        for status, old_response in old_responses.items():
            status = str(status)
            if status not in normalized_new_responses:
                continue
            _compare_response(
                operation_id,
                status,
                old_response,
                normalized_new_responses[status],
                baseline,
                current,
                failures,
            )
    return failures


def load_baseline(ref: str) -> JsonObject | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{OPENAPI_PATH}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        return None
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise TypeError("OpenAPI baseline is not a JSON object")
    return parsed


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ref", nargs="?", default="origin/main", help="Git baseline ref"
    )
    parser.add_argument(
        "--allow-missing-baseline",
        action="store_true",
        help="explicitly allow an initial contract freeze when the baseline file is absent",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        baseline = load_baseline(args.ref)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"Unable to parse OpenAPI baseline at {args.ref}:{OPENAPI_PATH}: {exc}")
        return 2
    if baseline is None:
        message = f"OpenAPI baseline is unavailable at {args.ref}:{OPENAPI_PATH}."
        if args.allow_missing_baseline:
            print(f"{message} Initial contract freeze was explicitly allowed.")
            return 0
        print(
            f"{message} Fetch the PR base ref, or use --allow-missing-baseline only "
            "for an intentional initial freeze."
        )
        return 2

    try:
        current = json.loads((ROOT / OPENAPI_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to read current OpenAPI document at {OPENAPI_PATH}: {exc}")
        return 2
    if not isinstance(current, dict):
        print(f"Current OpenAPI document at {OPENAPI_PATH} is not a JSON object.")
        return 2

    try:
        failures = find_breaking_changes(baseline, current)
    except ValueError as exc:
        print(f"Unable to compare OpenAPI documents: {exc}")
        return 2
    if failures:
        print("Breaking OpenAPI changes detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"No breaking OpenAPI change detected against {args.ref}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
