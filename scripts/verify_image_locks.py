"""Ensure every third-party runtime image is immutable and recorded."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "infra" / "versions.lock.json"
IMAGE_PATTERN = re.compile(r"^\s*image:\s*([^\s#]+)", re.MULTILINE)
FROM_PATTERN = re.compile(r"^FROM\s+([^\s]+)", re.MULTILINE)
DIGEST_PATTERN = re.compile(r"@sha256:([0-9a-f]{64})$")


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    locked = {
        f"{item['reference']}@{item['index_digest']}": item
        for item in lock["images"]
    }
    references = set(IMAGE_PATTERN.findall((ROOT / "compose.yaml").read_text("utf-8")))
    for dockerfile in sorted((ROOT / "infra").rglob("*Dockerfile")):
        references.update(FROM_PATTERN.findall(dockerfile.read_text("utf-8")))
    for dockerfile in sorted((ROOT / "infra").rglob("*.Dockerfile")):
        references.update(FROM_PATTERN.findall(dockerfile.read_text("utf-8")))

    failures: list[str] = []
    external = {
        reference
        for reference in references
        if not reference.startswith("biaice/") and "${" not in reference
    }
    for reference in sorted(external):
        if DIGEST_PATTERN.search(reference) is None:
            failures.append(f"image is not pinned by sha256: {reference}")
        elif reference not in locked:
            failures.append(f"image is absent from infra/versions.lock.json: {reference}")
    unused = set(locked) - external
    if unused:
        failures.append(f"version lock contains unused images: {sorted(unused)}")
    if failures:
        print("Image lock validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Image lock validation passed for {len(external)} immutable images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
