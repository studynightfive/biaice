"""Validate and print the fail-closed M0 contract coverage report."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts"


def operations(schema: dict[str, Any]):
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and operation.get("operationId"):
                yield method.upper(), path, operation


def main() -> int:
    schema = json.loads(
        (CONTRACTS / "openapi.generated.json").read_text(encoding="utf-8")
    )
    traceability = json.loads(
        (CONTRACTS / "traceability.generated.json").read_text(encoding="utf-8")
    )
    rows = {
        row["operation_id"]: row
        for group in traceability.values()
        for row in group
    }
    failures: list[str] = []
    counts: Counter[str] = Counter()
    fr_counts: Counter[str] = Counter()
    seen: set[str] = set()

    for method, path, operation in operations(schema):
        operation_id = operation["operationId"]
        seen.add(operation_id)
        row = rows.get(operation_id)
        if row is None:
            failures.append(f"{operation_id}: missing traceability row")
            continue
        expected = {
            "method": method,
            "path": path,
            "owner": operation.get("x-owner"),
            "permission": operation.get("x-required-permission"),
            "contract_only": operation.get("x-contract-only"),
        }
        for key, value in expected.items():
            if row.get(key) != value:
                failures.append(
                    f"{operation_id}: traceability {key}={row.get(key)!r}, "
                    f"OpenAPI={value!r}"
                )
        fr = operation.get("x-fr")
        if not fr:
            failures.append(f"{operation_id}: missing FR ownership")
        else:
            fr_counts[str(fr)] += 1
        if operation.get("x-contract-only"):
            counts["CONTRACT_ONLY"] += 1
            if row.get("schema_status") != "STUB_FIELDS_PENDING_OWNER_FREEZE":
                failures.append(f"{operation_id}: contract-only schema is not blocked")
            if row.get("test_status") != "M0_CONTRACT_TEST_ONLY":
                failures.append(f"{operation_id}: contract-only test status is ambiguous")
        else:
            counts["FOUNDATION_IMPLEMENTED"] += 1
            if row.get("schema_status") != "FROZEN":
                failures.append(f"{operation_id}: implemented schema is not frozen")
            if row.get("test_status") != "FOUNDATION_TESTED":
                failures.append(f"{operation_id}: implemented operation lacks test mapping")

    extra = set(rows) - seen
    if extra:
        failures.append(f"traceability contains unknown operations: {sorted(extra)}")

    lines = [
        "## M0 contract status",
        "",
        "| Status | Operations |",
        "| --- | ---: |",
        f"| Foundation implemented/tested | {counts['FOUNDATION_IMPLEMENTED']} |",
        f"| Contract-only, owner field freeze pending | {counts['CONTRACT_ONLY']} |",
        f"| Total | {len(seen)} |",
        "",
        "| FR group | Operations |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {fr} | {count} |" for fr, count in sorted(fr_counts.items()))
    lines.extend(
        [
            "",
            "Contract-only operations are deliberately blocked with RFC 7807 501; ",
            "they are not counted as implemented business functionality.",
        ]
    )
    report = "\n".join(lines) + "\n"
    print(report)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(report)
    if failures:
        print("Contract status validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
