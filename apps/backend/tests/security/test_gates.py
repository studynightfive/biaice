from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from biaice.core.config import Settings
from biaice.core.errors import BiaiceError
from biaice.core.security.gates import (
    EvidenceStatus,
    GateEvidence,
    GateName,
    GateService,
    GateStatus,
    build_machine_assessment,
    required_evidence,
)
from biaice.main import create_app

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


def evidence(key: str, status: EvidenceStatus = EvidenceStatus.PASS) -> GateEvidence:
    return GateEvidence(
        evidence_key=key,
        status=status,
        checked_at=NOW,
        checker="machine:test",
        evidence_hash=hashlib.sha256(key.encode()).hexdigest(),
        expires_at=NOW + timedelta(hours=1),
    )


def test_missing_or_unknown_evidence_never_passes() -> None:
    assessment = build_machine_assessment(
        gate_name=GateName.REAL_DATA_MODE,
        evidence=[evidence(next(iter(required_evidence(GateName.REAL_DATA_MODE))))],
        responsible_party="security-owner",
        assessed_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    assert assessment.status == GateStatus.UNKNOWN
    assert assessment.waiver_policy == "PROHIBITED"


def test_complete_machine_evidence_can_build_pass_assessment() -> None:
    assessment = build_machine_assessment(
        gate_name=GateName.BYOK_SECRET_GATE,
        evidence=[
            evidence(key) for key in required_evidence(GateName.BYOK_SECRET_GATE)
        ],
        responsible_party="security-owner",
        assessed_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    assert assessment.status == GateStatus.PASS


def test_default_gate_provider_is_unknown_and_require_fails_closed() -> None:
    service = GateService(
        Settings(environment="test", deployment_profile="secure_https")
    )
    assert service.current(GateName.REAL_DATA_MODE).status == GateStatus.UNKNOWN
    with pytest.raises(BiaiceError) as error:
        service.require(GateName.REAL_DATA_MODE)
    assert error.value.code == "REAL_DATA_MODE_REQUIRED"


def test_real_data_requested_refuses_application_start_without_machine_pass() -> None:
    app = create_app(
        settings=Settings(
            environment="test",
            deployment_profile="secure_https",
            real_data_mode_requested=True,
        )
    )
    with pytest.raises(BiaiceError) as error:
        with TestClient(app):
            pass
    assert error.value.code == "REAL_DATA_MODE_REQUIRED"
