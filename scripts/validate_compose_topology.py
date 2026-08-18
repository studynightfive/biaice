"""Validate the fail-closed Docker Compose network and port topology."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_BASE_SERVICES = {
    "gateway",
    "web",
    "api",
    "migrate",
    "worker-ingest",
    "worker-simulation",
    "worker-governance",
    "worker-provider",
    "scheduler",
    "postgres",
    "redis-broker",
    "redis-cache",
    "minio",
    "minio-init",
    "keycloak",
    "openbao",
    "clamav",
}
FAIL_CLOSED_SERVICES = {
    "web",
    "api",
    "worker-ingest",
    "worker-simulation",
    "worker-governance",
    "worker-provider",
    "scheduler",
}


def compose_config(*profiles: str) -> dict[str, Any]:
    command = ["docker", "compose", "--env-file", ".env.example"]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["config", "--format", "json"])
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def networks_for(service: dict[str, Any]) -> set[str]:
    networks = service.get("networks", {})
    networks_dict = networks if isinstance(networks, dict) else {}
    return set(networks_dict)


def main() -> int:
    failures: list[str] = []
    try:
        base = compose_config()
        complete = compose_config("provider-egress", "maintenance-egress", "observability")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Unable to render Compose config: {exc}", file=sys.stderr)
        return 1

    base_services = base.get("services", {})
    missing = REQUIRED_BASE_SERVICES - base_services.keys()
    if missing:
        failures.append(f"missing base services: {', '.join(sorted(missing))}")

    all_services = complete.get("services", {})
    for name, service in all_services.items():
        if service.get("ports") and name != "gateway":
            failures.append(f"{name} publishes a host port; only gateway may publish")

    gateway_ports = base_services.get("gateway", {}).get("ports", [])
    if not any(str(port.get("published")) == "8080" for port in gateway_ports):
        failures.append("synthetic gateway must publish port 8080")

    base_networks = base.get("networks", {})
    for name in ("front", "back"):
        if not base_networks.get(name, {}).get("internal", False):
            failures.append(f"{name} network must be internal")

    if base_networks.get("host-ingress", {}).get("internal", False):
        failures.append("host-ingress network must be host-routable")
    ingress_users = {
        name for name, service in all_services.items() if "host-ingress" in networks_for(service)
    }
    if ingress_users != {"gateway"}:
        failures.append(
            "host-ingress network users must be exactly gateway; "
            f"got {sorted(ingress_users)}"
        )

    provider_users = {
        name for name, service in all_services.items() if "provider-egress" in networks_for(service)
    }
    if provider_users != {"provider-egress-gateway"}:
        failures.append(
            "provider-egress network users must be exactly provider-egress-gateway; "
            f"got {sorted(provider_users)}"
        )

    maintenance_users = {
        name for name, service in all_services.items() if "maintenance-egress" in networks_for(service)
    }
    if maintenance_users != {"clamav-signature-update"}:
        failures.append(
            "maintenance-egress must be isolated to the maintenance updater; "
            f"got {sorted(maintenance_users)}"
        )

    for name in FAIL_CLOSED_SERVICES:
        environment = base_services.get(name, {}).get("environment", {})
        if str(environment.get("REAL_DATA_MODE", "")).lower() != "false":
            failures.append(f"{name} must default REAL_DATA_MODE=false")
        if str(environment.get("BIAICE_REAL_DATA_MODE_REQUESTED", "")).lower() != "false":
            failures.append(f"{name} must default BIAICE_REAL_DATA_MODE_REQUESTED=false")
        if str(environment.get("PROVIDER_EGRESS_ENABLED", "")).lower() != "false":
            failures.append(f"{name} must default PROVIDER_EGRESS_ENABLED=false")
        if str(environment.get("BYOK_SECRET_GATE", "")).upper() not in {"FAIL", "FALSE"}:
            failures.append(f"{name} must default BYOK_SECRET_GATE=FAIL")
        if str(environment.get("BIAICE_BYOK_ENABLED", "")).lower() != "false":
            failures.append(f"{name} must default BIAICE_BYOK_ENABLED=false")

    for name in ("web", "api", "worker-ingest", "worker-simulation", "worker-governance"):
        if "provider-egress" in networks_for(all_services.get(name, {})):
            failures.append(f"{name} must not join provider-egress")

    if failures:
        print("Compose topology validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Compose topology validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
