"""Tenant-scoped object storage port; browsers never receive MinIO credentials."""

from __future__ import annotations

from datetime import datetime
from typing import BinaryIO, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import TenantScope


class StorageObjectRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    object_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    bucket: str
    key: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)
    created_at: datetime
    encryption_key_reference: str | None = None


def scoped_storage_key(
    scope: TenantScope,
    namespace: str,
    object_id: UUID,
    *,
    project_id: UUID | None = None,
    decision_unit_id: UUID | None = None,
) -> str:
    scope.assert_allows(
        tenant_id=scope.tenant_id,
        data_domain_id=scope.data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
    )
    safe_namespace = namespace.strip("/").replace("..", "")
    project_segment = f"projects/{project_id}" if project_id else "projects/_tenant"
    unit_segment = f"units/{decision_unit_id}" if decision_unit_id else "units/_project"
    return (
        f"tenants/{scope.tenant_id}/domains/{scope.data_domain_id}/"
        f"{project_segment}/{unit_segment}/{safe_namespace}/{object_id}"
    )


class StoragePort(Protocol):
    def put(
        self,
        *,
        scope: TenantScope,
        namespace: str,
        object_id: UUID,
        stream: BinaryIO,
        expected_sha256: str,
    ) -> StorageObjectRef: ...

    def open(self, *, scope: TenantScope, object_ref: StorageObjectRef) -> BinaryIO: ...

    def logically_block(
        self, *, scope: TenantScope, object_ref: StorageObjectRef
    ) -> None: ...


class DeniedStoragePort:
    def put(self, **kwargs: object) -> StorageObjectRef:
        del kwargs
        raise RuntimeError("storage adapter is not configured")

    def open(self, **kwargs: object) -> BinaryIO:
        del kwargs
        raise RuntimeError("storage adapter is not configured")

    def logically_block(self, **kwargs: object) -> None:
        del kwargs
        raise RuntimeError("storage adapter is not configured")
