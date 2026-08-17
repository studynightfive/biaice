"""Strict, redacted contracts for Provider catalog and tenant configuration APIs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator

from biaice.core.security.restricted_ports import CredentialUsageScope
from biaice.modules.model_governance.domain.models import FrozenModel, Sha256

NonEmptyTuple = Annotated[tuple[str, ...], Field(min_length=1, max_length=50)]


class ProviderCatalogState(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    REVOKED = "REVOKED"


class ProviderActivationState(StrEnum):
    INACTIVE = "INACTIVE"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class ProviderCredentialState(StrEnum):
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"
    VALID = "VALID"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class ProviderHealth(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderValidity(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class ProviderRotationMode(StrEnum):
    PLANNED = "PLANNED"
    COMPROMISE = "COMPROMISE"


class ProviderInvocationState(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    TIMED_OUT = "TIMED_OUT"


class ProviderCatalogEntryCreate(FrozenModel):
    provider_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    provider_legal_name: str = Field(min_length=1, max_length=300)
    provider_model_id: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=300)
    api_host: str = Field(min_length=3, max_length=253)
    adapter_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    capabilities: NonEmptyTuple
    regions: NonEmptyTuple
    allowed_purposes: NonEmptyTuple
    max_input_tokens: int = Field(ge=1, le=10_000_000)
    redaction_policy_summary: str = Field(min_length=1, max_length=1000)
    training_use: Literal["DISABLED"] = "DISABLED"
    retention_days: int = Field(ge=0, le=36500)

    @field_validator("api_host")
    @classmethod
    def approved_host_only(cls, value: str) -> str:
        normalized = value.strip().lower().rstrip(".")
        if (
            "://" in normalized
            or "/" in normalized
            or ":" in normalized
            or normalized in {"localhost", "localhost.localdomain"}
            or normalized.startswith(("127.", "10.", "192.168.", "169.254."))
            or ".." in normalized
            or "." not in normalized
        ):
            raise ValueError("api_host must be a public DNS hostname without scheme, port or path")
        return normalized


class ProviderCatalogPublicEntry(FrozenModel):
    provider_id: str
    provider_legal_name: str
    provider_model_id: str
    display_name: str
    capabilities: tuple[str, ...]
    regions: tuple[str, ...]
    allowed_purposes: tuple[str, ...]
    max_input_tokens: int
    redaction_policy_summary: str
    training_use: Literal["DISABLED"]
    retention_days: int


class ProviderCatalogCreate(FrozenModel):
    entries: Annotated[tuple[ProviderCatalogEntryCreate, ...], Field(min_length=1, max_length=500)]
    reason_code: str = Field(min_length=3, max_length=120)

    @model_validator(mode="after")
    def unique_provider_models(self) -> "ProviderCatalogCreate":
        keys = {(item.provider_id, item.provider_model_id) for item in self.entries}
        if len(keys) != len(self.entries):
            raise ValueError("provider_id/provider_model_id pairs must be unique")
        return self


class ProviderCatalogDecision(FrozenModel):
    reason_code: str = Field(min_length=3, max_length=120)
    approval_evidence_hash: Sha256


class ProviderCatalogVersion(FrozenModel):
    catalog_id: UUID
    version_number: int = Field(ge=1)
    state: ProviderCatalogState
    catalog_hash: Sha256
    entries: tuple[ProviderCatalogEntryCreate, ...]
    created_at: datetime
    created_by: UUID
    reason_code: str
    published_at: datetime | None = None
    published_by: UUID | None = None
    approval_evidence_hash: Sha256 | None = None
    revoked_at: datetime | None = None
    revoked_by: UUID | None = None
    revocation_reason: str | None = None


class PublishedProviderCatalog(FrozenModel):
    catalog_id: UUID | None = None
    catalog_hash: Sha256 | None = None
    published_at: datetime | None = None
    items: tuple[ProviderCatalogPublicEntry, ...] = ()


class ProviderConfigurationCreate(FrozenModel):
    catalog_id: UUID
    catalog_hash: Sha256
    provider_id: str = Field(min_length=1, max_length=120)
    provider_model_id: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=200)
    monthly_budget_minor: int = Field(ge=0, le=10**15)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    timeout_seconds: int = Field(ge=1, le=600)
    retention_days: int = Field(ge=0, le=36500)
    legal_basis_evidence_id: UUID
    provider_policy_id: UUID
    pia_record_id: UUID
    cross_border_assessment_id: UUID


class ProviderConfigurationUpdate(FrozenModel):
    purpose: str | None = Field(default=None, min_length=1, max_length=200)
    monthly_budget_minor: int | None = Field(default=None, ge=0, le=10**15)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    retention_days: int | None = Field(default=None, ge=0, le=36500)
    legal_basis_evidence_id: UUID | None = None
    provider_policy_id: UUID | None = None
    pia_record_id: UUID | None = None
    cross_border_assessment_id: UUID | None = None

    @model_validator(mode="after")
    def at_least_one_change(self) -> "ProviderConfigurationUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one configuration field is required")
        return self


class ProviderConfigurationSuccessorCreate(FrozenModel):
    rotation_mode: ProviderRotationMode
    reason_code: str = Field(min_length=3, max_length=120)


class ProviderActionCommand(FrozenModel):
    reason_code: str = Field(min_length=3, max_length=120)


class ProviderCredentialWrite(FrozenModel):
    api_key: SecretStr = Field(
        min_length=8,
        max_length=8192,
        json_schema_extra={"writeOnly": True},
    )


class ProviderCredentialMetadata(FrozenModel):
    credential_reference_id: UUID
    credential_version: int = Field(ge=1)
    fingerprint: str = Field(min_length=16, max_length=256)
    last_four: str = Field(min_length=4, max_length=4)
    created_at: datetime
    expires_at: datetime | None = None


class ProviderCredentialReceipt(ProviderCredentialMetadata):
    credential_state: ProviderCredentialState
    credential_usage_scope: CredentialUsageScope


class AIProviderConfiguration(FrozenModel):
    config_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    version_number: int = Field(ge=1)
    current: bool
    catalog_id: UUID
    catalog_hash: Sha256
    provider_id: str
    provider_model_id: str
    purpose: str
    monthly_budget_minor: int
    currency: str
    timeout_seconds: int
    retention_days: int
    legal_basis_evidence_id: UUID
    provider_policy_id: UUID
    pia_record_id: UUID
    cross_border_assessment_id: UUID
    activation_state: ProviderActivationState
    credential_state: ProviderCredentialState
    credential_usage_scope: CredentialUsageScope
    credential: ProviderCredentialMetadata | None = None
    provider_health: ProviderHealth
    validity_state: ProviderValidity
    gate_reason_codes: tuple[str, ...] = ()
    supersedes_config_id: UUID | None = None
    rotation_mode: ProviderRotationMode | None = None
    state_version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID
    last_tested_at: datetime | None = None


class ProviderConfigurationPage(FrozenModel):
    items: tuple[AIProviderConfiguration, ...]
    next_cursor: str | None = None
    has_more: bool = False


class ProviderConnectionTestResult(FrozenModel):
    invocation_id: UUID
    reachable: bool
    authenticated: bool
    model_available: bool
    rate_limited: bool
    provider_health: ProviderHealth
    stable_error_code: str | None = None
    tested_at: datetime


class ProviderDeletionAccepted(FrozenModel):
    job_id: UUID
    state: Literal["QUEUED"] = "QUEUED"
    status_url: str
    credential_state: ProviderCredentialState
    credential_usage_scope: CredentialUsageScope


class ProviderInvocationRecord(FrozenModel):
    invocation_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    config_id: UUID
    provider_id: str
    provider_model_id: str
    purpose: Literal["CONNECTION_TEST"]
    state: ProviderInvocationState
    attempt: int = Field(ge=1)
    started_at: datetime
    completed_at: datetime
    request_hash: Sha256
    response_hash: Sha256 | None = None
    cost_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    stable_error_code: str | None = None
    derived_asset_refs: tuple[str, ...] = ()


class ProviderInvocationPage(FrozenModel):
    items: tuple[ProviderInvocationRecord, ...]
    next_cursor: str | None = None
    has_more: bool = False
