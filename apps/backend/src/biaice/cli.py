"""Idempotent one-shot command entrypoints used by Compose."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from biaice.core.config import get_settings
from biaice.core.security.gates import GateName, GateService


def backend_root() -> Path:
    configured = os.environ.get("BIAICE_BACKEND_ROOT")
    candidates = [
        Path(configured) if configured else None,
        Path.cwd(),
        Path.cwd() / "apps" / "backend",
        Path(__file__).resolve().parents[2],
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        resolved = candidate.resolve()
        if (resolved / "alembic.ini").is_file() and (resolved / "migrations").is_dir():
            return resolved
    raise RuntimeError("Could not locate alembic.ini and migrations; set BIAICE_BACKEND_ROOT")


def migrate() -> int:
    root = backend_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(config, "head")
    return 0


def seed_synthetic() -> int:
    # Identity seeds belong to Keycloak initialization. Domain fixtures belong
    # to module owners. This command is intentionally an idempotent M0 marker.
    print(json.dumps({"status": "ok", "mode": "synthetic-only", "domain_rows_created": 0}))
    return 0


def check_gates() -> int:
    service = GateService(get_settings())
    payload = {gate.value: service.current(gate).model_dump(mode="json") for gate in GateName}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="biaice")
    parser.add_argument("command", choices=["migrate", "seed-synthetic", "check-gates"])
    args = parser.parse_args()
    if args.command == "migrate":
        return migrate()
    if args.command == "seed-synthetic":
        return seed_synthetic()
    return check_gates()


if __name__ == "__main__":
    raise SystemExit(main())
