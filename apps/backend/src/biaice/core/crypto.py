"""Envelope-encryption application port; secure adapters live in infrastructure."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import TenantScope


class EncryptedPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    payload_id: UUID
    ciphertext_object_id: UUID
    ciphertext_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    plaintext_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    algorithm: str = "AES-256-GCM"
    wrapped_dek_reference: str
    kek_version: int = Field(ge=1)
    nonce_b64: str
    authentication_tag_b64: str


class EnvelopeEncryptionPort(Protocol):
    def encrypt(
        self,
        *,
        scope: TenantScope,
        payload_id: UUID,
        plaintext: bytes,
        associated_data: bytes,
    ) -> EncryptedPayload: ...

    def decrypt(
        self,
        *,
        scope: TenantScope,
        encrypted: EncryptedPayload,
        associated_data: bytes,
    ) -> bytes: ...

    def rewrap_dek(
        self, *, scope: TenantScope, encrypted: EncryptedPayload
    ) -> EncryptedPayload: ...

    def destroy_dek(
        self, *, scope: TenantScope, encrypted: EncryptedPayload
    ) -> None: ...

    def verify_recovery(
        self, *, scope: TenantScope, encrypted: EncryptedPayload
    ) -> bool: ...


class DeniedEnvelopeEncryptionPort:
    def _deny(self) -> None:
        raise RuntimeError("secure envelope-encryption adapter is not configured")

    def encrypt(self, **kwargs: object) -> EncryptedPayload:
        del kwargs
        self._deny()
        raise AssertionError("unreachable")

    def decrypt(self, **kwargs: object) -> bytes:
        del kwargs
        self._deny()
        raise AssertionError("unreachable")

    def rewrap_dek(self, **kwargs: object) -> EncryptedPayload:
        del kwargs
        self._deny()
        raise AssertionError("unreachable")

    def destroy_dek(self, **kwargs: object) -> None:
        del kwargs
        self._deny()

    def verify_recovery(self, **kwargs: object) -> bool:
        del kwargs
        self._deny()
        return False
