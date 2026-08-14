"""Machine-verifiable REAL_DATA_MODE and BYOK_SECRET_GATE predicates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from biaice.core.config import Settings
from biaice.core.errors import BiaiceError


class GateName(StrEnum):
    REAL_DATA_MODE = "REAL_DATA_MODE"
    BYOK_SECRET_GATE = "BYOK_SECRET_GATE"


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class GateValidity(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"


class EvidenceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class WaiverPolicy(StrEnum):
    PROHIBITED = "PROHIBITED"
    ALLOWED = "ALLOWED"


REAL_DATA_REQUIRED_EVIDENCE = frozenset(
    {
        "trusted_tls_oidc_mfa",
        "all_storage_scope_isolation",
        "encryption_and_key_separation",
        "append_only_audit_integrity",
        "secure_file_ingestion",
        "processing_basis_incident_privacy",
        "retention_deletion_tombstone_restore",
        "default_deny_egress",
        "security_scans",
        "least_privilege_dual_control",
        "backup_and_recovery_drills",
        "frozen_load_profile_and_evidence",
    }
)

BYOK_REQUIRED_EVIDENCE = frozenset(
    {
        "trusted_https_reauth_mfa_csrf",
        "openbao_secure_approles_audit",
        "secret_scope_isolation",
        "catalog_egress_network_controls",
        "secret_non_disclosure_scans_restore",
        "signed_current_assessment",
    }
)


class GateEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_key: str
    status: EvidenceStatus
    checked_at: datetime
    checker: str
    evidence_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: datetime


class GateAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    assessment_id: UUID
    gate_name: GateName
    status: GateStatus
    validity: GateValidity
    assessed_at: datetime
    expires_at: datetime
    responsible_party: str
    evidence: tuple[GateEvidence, ...]
    evidence_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    waiver_policy: WaiverPolicy = WaiverPolicy.PROHIBITED
    reason_codes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def mandatory_gates_never_allow_waiver(self) -> "GateAssessment":
        if self.gate_name in {GateName.REAL_DATA_MODE, GateName.BYOK_SECRET_GATE}:
            if self.waiver_policy != WaiverPolicy.PROHIBITED:
                raise ValueError("REAL_DATA_MODE and BYOK_SECRET_GATE prohibit waivers")
        return self

    @property
    def is_pass_current(self) -> bool:
        now = datetime.now(timezone.utc)
        return (
            self.status == GateStatus.PASS
            and self.validity == GateValidity.CURRENT
            and self.expires_at > now
        )


class GateEvidenceProvider(Protocol):
    def current(self, gate_name: GateName) -> GateAssessment | None: ...


class NullGateEvidenceProvider:
    def current(self, gate_name: GateName) -> GateAssessment | None:
        del gate_name
        return None


class InMemoryGateEvidenceProvider:
    """Test/contract provider; secure deployment replaces this with signed evidence storage."""

    def __init__(self, assessments: Sequence[GateAssessment] = ()) -> None:
        self._assessments = {
            assessment.gate_name: assessment for assessment in assessments
        }

    def current(self, gate_name: GateName) -> GateAssessment | None:
        return self._assessments.get(gate_name)


def required_evidence(gate_name: GateName) -> frozenset[str]:
    if gate_name == GateName.REAL_DATA_MODE:
        return REAL_DATA_REQUIRED_EVIDENCE
    return BYOK_REQUIRED_EVIDENCE


def build_machine_assessment(
    *,
    gate_name: GateName,
    evidence: Sequence[GateEvidence],
    responsible_party: str,
    assessed_at: datetime,
    expires_at: datetime,
) -> GateAssessment:
    supplied = {item.evidence_key: item for item in evidence}
    required = required_evidence(gate_name)
    missing = sorted(required - supplied.keys())
    failed = sorted(
        key
        for key in required
        if key in supplied and supplied[key].status == EvidenceStatus.FAIL
    )
    unknown = sorted(
        key
        for key in required
        if key in supplied and supplied[key].status == EvidenceStatus.UNKNOWN
    )
    expired = sorted(
        key
        for key in required
        if key in supplied and supplied[key].expires_at <= assessed_at
    )
    if failed:
        status = GateStatus.FAIL
    elif missing or unknown or expired:
        status = GateStatus.UNKNOWN
    else:
        status = GateStatus.PASS
    reasons = tuple(
        [
            *(f"MISSING:{key}" for key in missing),
            *(f"FAILED:{key}" for key in failed),
            *(f"UNKNOWN:{key}" for key in unknown),
            *(f"EXPIRED:{key}" for key in expired),
        ]
    )
    canonical = [
        item.model_dump(mode="json")
        for item in sorted(evidence, key=lambda item: item.evidence_key)
    ]
    evidence_hash = hashlib.sha256(
        json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    return GateAssessment(
        assessment_id=uuid4(),
        gate_name=gate_name,
        status=status,
        validity=GateValidity.CURRENT
        if expires_at > assessed_at
        else GateValidity.STALE,
        assessed_at=assessed_at,
        expires_at=expires_at,
        responsible_party=responsible_party,
        evidence=tuple(evidence),
        evidence_hash=evidence_hash,
        waiver_policy=WaiverPolicy.PROHIBITED,
        reason_codes=reasons,
    )


class GateService:
    def __init__(
        self, settings: Settings, provider: GateEvidenceProvider | None = None
    ) -> None:
        self.settings = settings
        self.provider = provider or NullGateEvidenceProvider()

    def current(self, gate_name: GateName) -> GateAssessment:
        assessment = self.provider.current(gate_name)
        if assessment is not None:
            if (
                assessment.expires_at <= datetime.now(timezone.utc)
                and assessment.validity == GateValidity.CURRENT
            ):
                return assessment.model_copy(update={"validity": GateValidity.STALE})
            return assessment
        now = datetime.now(timezone.utc)
        return GateAssessment(
            assessment_id=UUID(int=0),
            gate_name=gate_name,
            status=GateStatus.UNKNOWN,
            validity=GateValidity.STALE,
            assessed_at=now,
            expires_at=now,
            responsible_party="UNASSIGNED",
            evidence=(),
            evidence_hash=hashlib.sha256(b"").hexdigest(),
            waiver_policy=WaiverPolicy.PROHIBITED,
            reason_codes=("MACHINE_ASSESSMENT_MISSING",),
        )

    def require(self, gate_name: GateName) -> GateAssessment:
        assessment = self.current(gate_name)
        if not assessment.is_pass_current:
            code = (
                "REAL_DATA_MODE_REQUIRED"
                if gate_name == GateName.REAL_DATA_MODE
                else "BYOK_SECRET_GATE_REQUIRED"
            )
            raise BiaiceError(
                code,
                detail=f"{gate_name.value} must be PASS/CURRENT; current state is {assessment.status}/{assessment.validity}.",
            )
        return assessment

    def assert_startup_allowed(self) -> None:
        if self.settings.real_data_mode_requested:
            self.require(GateName.REAL_DATA_MODE)
        if self.settings.byok_enabled:
            self.require(GateName.BYOK_SECRET_GATE)


class RequireRealDataMode:
    def __call__(self, service: GateService) -> GateAssessment:
        return service.require(GateName.REAL_DATA_MODE)


class RequireBYOKSecretGate:
    """Run this guard before a credential request body is parsed."""

    def __call__(self, service: GateService) -> GateAssessment:
        return service.require(GateName.BYOK_SECRET_GATE)
