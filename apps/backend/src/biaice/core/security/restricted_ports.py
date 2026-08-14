"""Restricted platform ports. These are intentionally not re-exported by core."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from biaice.core.auth import TenantScope


class CredentialUsageScope(StrEnum):
    TEST_ONLY = "TEST_ONLY"
    BUSINESS_AND_DELETION = "BUSINESS_AND_DELETION"
    DELETION_ONLY = "DELETION_ONLY"
    NONE = "NONE"


class SecretReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reference_id: UUID
    credential_version: int = Field(ge=1)
    fingerprint: str
    last_four: str = Field(min_length=4, max_length=4)
    usage_scope: CredentialUsageScope
    created_at: datetime
    expires_at: datetime | None = None


class SecretStorePort(Protocol):
    """Write/destroy only. Deliberately has no read/list plaintext method."""

    def write(
        self,
        *,
        scope: TenantScope,
        provider_id: str,
        purpose: str,
        plaintext: SecretStr,
    ) -> SecretReference: ...

    def rotate(
        self,
        *,
        scope: TenantScope,
        old_reference: SecretReference,
        plaintext: SecretStr,
    ) -> SecretReference: ...

    def restrict_to_deletion(
        self, *, scope: TenantScope, reference: SecretReference
    ) -> SecretReference: ...

    def destroy(self, *, scope: TenantScope, reference: SecretReference) -> None: ...


class EgressAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    invocation_id: UUID
    configuration_id: UUID
    credential_reference_id: UUID
    credential_version: int = Field(ge=1)
    purpose: str
    exact_host: str
    exact_model_id: str
    catalog_version: UUID
    catalog_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: datetime
    single_use_nonce: str
    signature: str


class EgressResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    invocation_id: UUID
    status_code: int
    request_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    response_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    stable_error_code: str | None = None


class ProviderEgressPort(Protocol):
    """Low-level egress, injectable only into the member-5 governed invocation adapter."""

    def invoke(
        self, *, authorization: EgressAuthorization, minimized_payload: bytes
    ) -> EgressResult: ...
