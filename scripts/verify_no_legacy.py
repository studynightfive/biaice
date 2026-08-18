"""Verify that Sites/Cloudflare runtime artifacts cannot re-enter the project."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATHS = {
    ".openai/hosting.json",
    "build/sites-vite-plugin.ts",
    "worker/index.ts",
    "vite.config.ts",
    "db/index.ts",
    "app/chatgpt-auth.ts",
}
FORBIDDEN_PACKAGES = {
    "vinext",
    "wrangler",
    "@cloudflare/vite-plugin",
    "@vitejs/plugin-rsc",
    "drizzle-kit",
    "drizzle-orm",
}


def main() -> int:
    tracked_raw = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    tracked = {
        item.decode("utf-8").replace("\\", "/")
        for item in tracked_raw.split(b"\0")
        if item
    }
    failures = [
        f"forbidden tracked path: {path}" for path in sorted(FORBIDDEN_PATHS & tracked)
    ]

    package_path = ROOT / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
    }
    for name in sorted(FORBIDDEN_PACKAGES & dependencies.keys()):
        failures.append(f"forbidden root package: {name}")

    runtime_markers = ("oai-authenticated-user", "git.chatgpt-team.site")
    for base in (ROOT / "apps", ROOT / "infra"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".ico",
            }:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in runtime_markers:
                if marker in text:
                    failures.append(
                        f"forbidden runtime marker {marker!r}: {path.relative_to(ROOT)}"
                    )

    if failures:
        print("Legacy runtime verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Legacy Sites/Cloudflare runtime verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
