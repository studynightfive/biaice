"""Transactional outbox and the local event-envelope contract."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from biaice.core.auth import TenantScope
from biaice.core.db import Base, TenantScopedMixin

EVENT_CATALOG: dict[str, dict[str, object]] = {
    "governance.invalidation.requested.v1": {
        "owner": "member-1",
        "description": "An effective upstream event requires dependency-matrix evaluation.",
        "payload_schema": "InvalidationRequestedV1",
    },
    "governance.invalidation.recorded.v1": {
        "owner": "member-1",
        "description": "A concrete downstream object was marked stale or invalidated.",
        "payload_schema": "InvalidationRecordedV1",
    },
    "governance.retention.expired.v1": {
        "owner": "member-1",
        "description": "Formal use was immediately blocked at retention expiry.",
        "payload_schema": "RetentionExpiredV1",
    },
    "governance.deletion.requested.v1": {
        "owner": "member-1",
        "description": "Logical access was blocked and replica deletion orchestration began.",
        "payload_schema": "DeletionRequestedV1",
    },
    "governance.deletion.completed.v1": {
        "owner": "member-1",
        "description": "Every required replica receipt was verified and a tombstone persisted.",
        "payload_schema": "DeletionCompletedV1",
    },
    "governance.tombstone.replay-required.v1": {
        "owner": "member-1",
        "description": "Recovery remains closed until tombstones are replayed.",
        "payload_schema": "TombstoneReplayRequiredV1",
    },
    "audit.integrity.failed.v1": {
        "owner": "member-1",
        "description": "Audit hash-chain or external-anchor validation failed.",
        "payload_schema": "AuditIntegrityFailedV1",
    },
}

for _event_name, _event_details in EVENT_CATALOG.items():
    _event_details.update(
        {
            "contract_only": False,
            "schema_status": "FROZEN_ENVELOPE_PAYLOAD_PENDING_PERSISTENCE",
            "source_name": _event_name,
        }
    )


def _register_contract_events(domain: str, owner: str, names: tuple[str, ...]) -> None:
    for name in names:
        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        EVENT_CATALOG[f"{domain}.{snake_name}.v1"] = {
            "owner": owner,
            "description": f"CONTRACT_ONLY domain event {name}; payload fields await the owner schema PR.",
            "payload_schema": f"{name}V1",
            "contract_only": True,
            "schema_status": "STUB_FIELDS_PENDING_OWNER_FREEZE",
            "source_name": name,
        }


_register_contract_events(
    "rules",
    "member-2",
    (
        "ScopeAssessmentPublished",
        "RegimePublished",
        "RuleSetPublished",
        "RuleSetRevoked",
        "CrossLotConstraintConfirmed",
        "DecisionUnitReopened",
        "DecisionUnitLifecycleAdvanced",
    ),
)
_register_contract_events(
    "documents",
    "member-3",
    (
        "SourceDocumentUploaded",
        "SourceDocumentReleased",
        "DocumentQuarantined",
        "ParseCompleted",
        "ParseFailed",
        "DerivedAssetRegistered",
        "ReplicaDeletionReceiptProduced",
    ),
)
_register_contract_events(
    "evidence_commercial",
    "member-4",
    (
        "EvidencePublished",
        "EvidenceRevoked",
        "EvidenceMatchReviewed",
        "ResponseProfilePublished",
        "PrecheckAssessed",
        "ConditionChanged",
        "CostBaselinePublished",
        "CommercialPolicyPublished",
        "ReadinessAssessed",
    ),
)
_register_contract_events(
    "model_governance",
    "member-5",
    (
        "CompetitorProfilePublished",
        "CompetitorProfileQuarantined",
        "MarketPriorPublished",
        "MarketPriorExpired",
        "UnknownEntrantPublished",
        "ProviderCatalogPublished",
        "ProviderCatalogRevoked",
        "ProviderConfigurationSuccessorCreated",
        "ProviderConfigurationSuperseded",
        "ProviderCredentialSet",
        "ProviderCredentialRotated",
        "ProviderCredentialUsageRestricted",
        "ProviderCredentialLocalReferenceDestroyed",
        "ProviderRemoteCredentialRevocationReceiptProduced",
        "ProviderConfigurationVerified",
        "ProviderConfigurationActivated",
        "ProviderConfigurationSuspended",
        "ProviderConfigurationRevoked",
        "ProcessingAuthorizationWithdrawn",
        "ProviderPolicyApproved",
        "ProviderPolicyExpired",
        "ProviderPolicyRevoked",
        "ProviderInvocationQueued",
        "ProviderInvocationStarted",
        "ProviderInvocationSucceeded",
        "ProviderInvocationFailed",
        "ProviderInvocationBlocked",
        "ProviderInvocationTimedOut",
        "ProviderInvocationCancelled",
        "ProviderReplicaDeletionReceiptProduced",
        "ModelDeploymentActivated",
        "ModelPolicyEffective",
        "ModelRolledBack",
    ),
)
_register_contract_events(
    "simulation",
    "member-6",
    (
        "DecisionBaselineFrozen",
        "ScenarioSetsFrozen",
        "SimulationStarted",
        "SimulationFailed",
        "SimulationAssessed",
        "StrategyPlansFinalized",
        "EligibilityAssessed",
        "SimulationSnapshotCreated",
    ),
)
_register_contract_events(
    "approvals_reports",
    "member-7",
    (
        "RiskAccepted",
        "RiskRevoked",
        "ApprovalPackageFrozen",
        "ApprovalPackageInvalidated",
        "ApprovalRequested",
        "ApprovalDecided",
        "SubmissionAuthorizationCreated",
        "SubmissionAuthorizationBlocked",
        "PrecheckReportCreated",
        "DecisionReportCreated",
        "DecisionReportRevoked",
        "SubmissionDrafted",
        "SubmissionDeclared",
        "SubmissionVerified",
        "SubmissionMismatch",
        "SubmissionFailed",
        "SubmissionWithdrawn",
        "OutcomeVerified",
        "OutcomeConflicting",
        "DecisionUnitTransitionRequested",
    ),
)


PROHIBITED_EVENT_KEYS = frozenset(
    {
        "body",
        "content",
        "plaintext",
        "api_key",
        "secret",
        "prompt",
        "model_response",
        "personal_data",
        "cost_detail",
        "raw_prompt",
        "response_body",
        "request_body",
        "raw_content",
        "document_text",
        "personal_information",
        "credential_plaintext",
        "access_token",
        "refresh_token",
        "authorization_header",
    }
)


def _reject_sensitive_keys(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            canonical_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).replace("-", "_").lower()
            if canonical_key in PROHIBITED_EVENT_KEYS:
                raise ValueError(f"sensitive event field is forbidden: {path}.{key}")
            _reject_sensitive_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_keys(nested, f"{path}[{index}]")


class EventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    event_type: str
    schema_version: int = Field(ge=1)
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    aggregate_type: str
    aggregate_id: UUID
    occurred_at: datetime
    actor_id: UUID | None = None
    request_id: str
    correlation_id: UUID
    causation_id: UUID | None = None
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def payload_must_be_deidentified(cls, value: dict[str, Any]) -> dict[str, Any]:
        _reject_sensitive_keys(value)
        return value


class OutboxEventRecord(Base, TenantScopedMixin):
    __tablename__ = "outbox_event"
    __table_args__ = (
        UniqueConstraint("tenant_id", "data_domain_id", "event_id", name="uq_outbox_scope_event"),
    )

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatch_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OutboxPort(Protocol):
    def append(self, *, scope: TenantScope, event: EventEnvelope) -> None: ...


class DeniedOutboxPort:
    def append(self, *, scope: TenantScope, event: EventEnvelope) -> None:
        del scope, event
        raise RuntimeError("transactional outbox is not configured")
