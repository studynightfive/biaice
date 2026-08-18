"""Regression tests for signed provider-egress Gate evidence."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PROXY_PATH = ROOT / "infra" / "provider-egress" / "proxy.py"
SPEC = importlib.util.spec_from_file_location(
    "biaice_provider_egress_proxy", PROXY_PATH
)
assert SPEC is not None and SPEC.loader is not None
PROXY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROXY
SPEC.loader.exec_module(PROXY)


class SignedGateEvidenceTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict[str, str]:
        domains = "api.example.com\n"
        allowlist = root / "provider-domains.txt"
        allowlist.write_text(domains, encoding="ascii")
        key = b"test-only-gate-verification-key-32-bytes-minimum"
        key_path = root / "gate-verification.key"
        key_path.write_bytes(key)
        gate = {
            "gate": "BYOK_SECRET_GATE",
            "status": "PASS",
            "validity_state": "CURRENT",
            "assessment_id": "test-assessment",
            "expires_at": "2999-01-01T00:00:00Z",
            "catalog_allowlist_sha256": hashlib.sha256(
                domains.encode("ascii")
            ).hexdigest(),
        }
        canonical = json.dumps(
            gate, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        gate["evidence_signature"] = (
            "hmac-sha256:" + hmac.new(key, canonical, hashlib.sha256).hexdigest()
        )
        gate_path = root / "byok-secret-gate.json"
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        return {
            "BIAICE_EGRESS_GATE_FILE": str(gate_path),
            "BIAICE_EGRESS_ALLOWLIST_FILE": str(allowlist),
            "BIAICE_EGRESS_GATE_VERIFICATION_KEY_FILE": str(key_path),
        }

    def test_valid_signed_current_gate_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            environment = self._fixture(Path(raw_root))
            with patch.dict(os.environ, environment, clear=False):
                state = PROXY.load_gate_state()
        self.assertEqual(state.domains, frozenset({"api.example.com"}))

    def test_tampered_gate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            environment = self._fixture(root)
            gate_path = Path(environment["BIAICE_EGRESS_GATE_FILE"])
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["assessment_id"] = "tampered"
            gate_path.write_text(json.dumps(gate), encoding="utf-8")
            with (
                patch.dict(os.environ, environment, clear=False),
                self.assertRaisesRegex(PROXY.Denied, "BYOK_GATE_SIGNATURE_INVALID"),
            ):
                PROXY.load_gate_state()


if __name__ == "__main__":
    unittest.main()
