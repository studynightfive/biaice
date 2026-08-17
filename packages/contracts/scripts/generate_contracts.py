"""Export deterministic contracts from FastAPI/Pydantic.

Run from the repository root:

    python packages/contracts/scripts/generate_contracts.py
    python packages/contracts/scripts/generate_contracts.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_SRC = REPOSITORY_ROOT / "apps" / "backend" / "src"
CONTRACT_ROOT = REPOSITORY_ROOT / "packages" / "contracts"
sys.path.insert(0, str(BACKEND_SRC))
os.environ.setdefault("BIAICE_ENVIRONMENT", "contract")

from biaice.core.config import Settings
from biaice.core.errors import ERROR_CATALOG
from biaice.core.outbox import EVENT_CATALOG, EventEnvelope
from biaice.main import create_app


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def operation_items(openapi: dict[str, Any]):
    for path, path_item in sorted(openapi["paths"].items()):
        for method, operation in sorted(path_item.items()):
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            yield method.upper(), path, operation


def validate_openapi(openapi: dict[str, Any]) -> None:
    seen: set[str] = set()
    errors: list[str] = []
    covered_frs: set[str] = set()
    for method, path, operation in operation_items(openapi):
        operation_id = operation.get("operationId")
        if not operation_id:
            errors.append(f"{method} {path}: missing operationId")
            continue
        if operation_id in seen:
            errors.append(f"duplicate operationId: {operation_id}")
        seen.add(operation_id)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", operation_id):
            errors.append(f"{operation_id}: operationId must be snake_case")
        for extension in (
            "x-owner",
            "x-fr",
            "x-required-permission",
            "x-contract-only",
        ):
            if extension not in operation:
                errors.append(f"{operation_id}: missing {extension}")
        covered_frs.add(operation.get("x-fr", ""))
        if (
            operation.get("x-contract-only")
            and operation.get("x-schema-status") != "STUB_FIELDS_PENDING_OWNER_FREEZE"
        ):
            errors.append(
                f"{operation_id}: contract-only route missing field-freeze status"
            )
        if operation.get("x-idempotency-required"):
            parameters = operation.get("parameters", [])
            if not any(
                item.get("in") == "header" and item.get("name") == "Idempotency-Key"
                for item in parameters
            ):
                errors.append(f"{operation_id}: idempotency metadata/header mismatch")
        if operation.get("x-etag-required"):
            parameters = operation.get("parameters", [])
            if not any(
                item.get("in") == "header" and item.get("name") == "If-Match"
                for item in parameters
            ):
                errors.append(f"{operation_id}: ETag metadata/header mismatch")
        for status_code, response in operation.get("responses", {}).items():
            if str(status_code).startswith(("4", "5")):
                content = response.get("content", {})
                if content and "application/problem+json" not in content:
                    errors.append(
                        f"{operation_id} response {status_code}: must use application/problem+json"
                    )
    required = {f"FR-{number:02d}" for number in range(1, 9)} | {
        "FR-09a",
        "FR-09b",
        "FR-10",
        "FR-11",
        "FR-12",
        "FR-13",
    }
    missing = required - covered_frs
    if missing:
        errors.append(f"missing P0 FR operation groups: {sorted(missing)}")
    if errors:
        raise RuntimeError("Contract validation failed:\n- " + "\n- ".join(errors))


def schema_ref_name(schema: dict[str, Any]) -> str | None:
    ref = schema.get("$ref")
    return ref.rsplit("/", 1)[-1] if ref else None


def ts_type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if "const" in schema:
        return json.dumps(schema["const"], ensure_ascii=False)
    if "enum" in schema:
        return " | ".join(
            json.dumps(value, ensure_ascii=False) for value in schema["enum"]
        )
    if "anyOf" in schema:
        return " | ".join(ts_type(item) for item in schema["anyOf"])
    if "oneOf" in schema:
        return " | ".join(ts_type(item) for item in schema["oneOf"])
    value_type = schema.get("type")
    if value_type == "array":
        return f"ReadonlyArray<{ts_type(schema.get('items', {}))}>"
    if value_type == "object":
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {ts_type(additional)}>"
        return "Record<string, unknown>"
    if value_type in {"integer", "number"}:
        return "number"
    if value_type == "boolean":
        return "boolean"
    if value_type == "null":
        return "null"
    if value_type == "string":
        return "string"
    return "unknown"


def generate_types(openapi: dict[str, Any]) -> str:
    lines = [
        "// Generated from openapi.generated.json. Do not edit.",
        "/* eslint-disable */",
        "",
    ]
    for name, schema in sorted(
        openapi.get("components", {}).get("schemas", {}).items()
    ):
        if schema.get("type") == "object" or "properties" in schema:
            required = set(schema.get("required", []))
            lines.append(f"export interface {name} {{")
            for property_name, property_schema in schema.get("properties", {}).items():
                optional = "" if property_name in required else "?"
                quoted = (
                    property_name
                    if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", property_name)
                    else json.dumps(property_name)
                )
                lines.append(
                    f"  readonly {quoted}{optional}: {ts_type(property_schema)};"
                )
            if not schema.get("properties"):
                lines.append("  readonly [key: string]: unknown;")
            lines.append("}")
        else:
            lines.append(f"export type {name} = {ts_type(schema)};")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def success_schema(operation: dict[str, Any]) -> str:
    for status_code, response in sorted(operation.get("responses", {}).items()):
        if str(status_code).startswith("2"):
            schema = (
                response.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            return ts_type(schema) if schema else "void"
    return "void"


def generate_client(openapi: dict[str, Any]) -> str:
    lines = [
        "// Generated from openapi.generated.json. Do not edit.",
        "/* eslint-disable */",
        'import type * as Models from "./types";',
        "",
        "export interface RequestOptions {",
        "  readonly path?: Readonly<Record<string, string | number>>;",
        "  readonly query?: Readonly<Record<string, string | number | boolean | undefined>>;",
        "  readonly body?: unknown;",
        "  readonly idempotencyKey?: string;",
        "  readonly ifMatch?: string;",
        "  readonly signal?: AbortSignal;",
        "}",
        "",
        "export class BiaiceProblem extends Error {",
        "  constructor(readonly problem: Models.ProblemDetails) { super(problem.detail); }",
        "}",
        "",
        "export class BiaiceClient {",
        '  constructor(private readonly baseUrl = "") {}',
        "  async request<T>(method: string, template: string, options: RequestOptions = {}): Promise<T> {",
        "    const path = template.replace(/\\{([^}]+)\\}/g, (_, key: string) => {",
        "      const value = options.path?.[key];",
        "      if (value === undefined) throw new Error(`Missing path parameter: ${key}`);",
        "      return encodeURIComponent(String(value));",
        "    });",
        "    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);",
        "    for (const [key, value] of Object.entries(options.query ?? {})) if (value !== undefined) url.searchParams.set(key, String(value));",
        '    const headers = new Headers({ Accept: "application/json, application/problem+json" });',
        '    if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);',
        '    if (options.ifMatch) headers.set("If-Match", options.ifMatch);',
        '    if (options.body !== undefined) headers.set("Content-Type", "application/json");',
        "    // Tenant/data-domain headers are intentionally unsupported; scope comes from the server session.",
        '    const response = await fetch(url, { method, credentials: "include", headers, body: options.body === undefined ? undefined : JSON.stringify(options.body), signal: options.signal });',
        "    if (!response.ok) throw new BiaiceProblem(await response.json() as Models.ProblemDetails);",
        "    if (response.status === 204) return undefined as T;",
        "    return await response.json() as T;",
        "  }",
        "}",
        "",
    ]
    for method, path, operation in operation_items(openapi):
        operation_id = operation["operationId"]
        return_type = success_schema(operation)
        if return_type not in {"void", "unknown"} and re.fullmatch(
            r"[A-Za-z_$][A-Za-z0-9_$]*", return_type
        ):
            return_type = f"Models.{return_type}"
        lines.extend(
            [
                f"export async function {operation_id}(client: BiaiceClient, options: RequestOptions = {{}}): Promise<{return_type}> {{",
                f"  return client.request<{return_type}>({json.dumps(method)}, {json.dumps(path)}, options);",
                "}",
                "",
            ]
        )
    return "\n".join(lines)


def build_outputs() -> dict[Path, str]:
    app = create_app(
        settings=Settings(environment="contract", deployment_profile="synthetic_http")
    )
    openapi = app.openapi()
    validate_openapi(openapi)
    error_catalog = {
        code: {
            "status": definition.status,
            "title": definition.title,
            "recoverable": definition.recoverable,
            "remediation": definition.remediation,
        }
        for code, definition in sorted(ERROR_CATALOG.items())
    }
    operation_catalog = [
        {
            "method": method,
            "path": path,
            "operation_id": operation["operationId"],
            "fr": operation["x-fr"],
            "owner": operation["x-owner"],
            "permission": operation["x-required-permission"],
            "contract_only": operation["x-contract-only"],
            "schema_status": operation.get("x-schema-status", "FROZEN"),
            "idempotency_required": operation.get("x-idempotency-required", False),
            "etag_required": operation.get("x-etag-required", False),
        }
        for method, path, operation in operation_items(openapi)
    ]
    traceability: dict[str, list[dict[str, object]]] = {}
    for operation in operation_catalog:
        traceability.setdefault(str(operation["fr"]), []).append(
            {
                "operation_id": operation["operation_id"],
                "method": operation["method"],
                "path": operation["path"],
                "owner": operation["owner"],
                "permission": operation["permission"],
                "contract_only": operation["contract_only"],
                "schema_status": operation["schema_status"],
                "test_status": "M0_CONTRACT_TEST_ONLY"
                if operation["contract_only"]
                else "FOUNDATION_TESTED",
            }
        )
    outputs = {
        CONTRACT_ROOT / "openapi.generated.json": json_text(openapi),
        CONTRACT_ROOT / "operation-catalog.generated.json": json_text(
            operation_catalog
        ),
        CONTRACT_ROOT / "traceability.generated.json": json_text(traceability),
        CONTRACT_ROOT / "error-catalog.yaml": json_text(error_catalog),
        CONTRACT_ROOT / "events" / "catalog.yaml": json_text(EVENT_CATALOG),
        CONTRACT_ROOT / "events" / "event-envelope.schema.json": json_text(
            EventEnvelope.model_json_schema()
        ),
        CONTRACT_ROOT / "generated-typescript" / "types.ts": generate_types(openapi),
        CONTRACT_ROOT / "generated-typescript" / "client.ts": generate_client(openapi),
        CONTRACT_ROOT
        / "generated-typescript"
        / "index.ts": 'export * from "./types";\nexport * from "./client";\n',
    }
    manifest = {
        str(path.relative_to(CONTRACT_ROOT)).replace("\\", "/"): hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()
        for path, content in sorted(outputs.items(), key=lambda item: str(item[0]))
    }
    outputs[CONTRACT_ROOT / "contracts-manifest.generated.json"] = json_text(manifest)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Fail if checked-in snapshots differ"
    )
    args = parser.parse_args()
    outputs = build_outputs()
    drift: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                drift.append(str(path.relative_to(REPOSITORY_ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    if drift:
        raise SystemExit("Contract drift detected:\n- " + "\n- ".join(drift))
    if not args.check:
        print(
            f"Generated {len(outputs)} contract artifacts from {len(list(operation_items(json.loads(outputs[CONTRACT_ROOT / 'openapi.generated.json']))))} operations."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
