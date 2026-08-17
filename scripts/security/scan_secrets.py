"""Fail CI when tracked files contain common high-confidence secret material."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    "OpenAI-style secret": re.compile(rb"sk-[A-Za-z0-9_-]{24,}"),
}
ALLOWED_ENV_FILES = {".env.example"}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.name.startswith(".env") and path.name not in ALLOWED_ENV_FILES:
            findings.append(f"forbidden environment file: {relative}")
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            continue
        data = path.read_bytes()
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append(f"{label}: {relative}")

    if findings:
        print("Sensitive material detected (values redacted):", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Tracked-file secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
