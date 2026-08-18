"""FR-11 application ports; member 3/5 implement only their replica adapters."""

from __future__ import annotations

from typing import Protocol, Sequence
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.governance.domain.models import (
    DeletionJob,
    DeletionReceipt,
    DeletionReplicaCommand,
    LegalHoldRecord,
    ReplicaKind,
    ReplicaLocation,
    ScopedObjectRef,
    TombstoneRecord,
)


class ReplicaDeletionAdapter(Protocol):
    """Narrow adapter boundary: it returns a receipt and never completes a job."""

    @property
    def adapter_name(self) -> str: ...

    @property
    def supported_kinds(self) -> frozenset[ReplicaKind]: ...

    def delete(self, *, scope: TenantScope, command: DeletionReplicaCommand) -> DeletionReceipt: ...


class DeletionReceiptVerifier(Protocol):
    def verify(
        self,
        *,
        scope: TenantScope,
        command: DeletionReplicaCommand,
        receipt: DeletionReceipt,
    ) -> DeletionReceipt: ...


class GovernanceRepository(Protocol):
    """Atomic persistence boundary; PostgreSQL is the only job truth."""

    def create_deletion_and_block_access(
        self,
        *,
        scope: TenantScope,
        target: ScopedObjectRef,
        requested_by: UUID,
        reason_code: str,
        idempotency_key: str,
    ) -> DeletionJob: ...

    def lock_deletion_job(
        self, *, scope: TenantScope, deletion_job_id: UUID
    ) -> DeletionJob | None: ...

    def save_deletion_job(self, *, scope: TenantScope, job: DeletionJob) -> None: ...

    def list_replicas(
        self, *, scope: TenantScope, target: ScopedObjectRef
    ) -> Sequence[ReplicaLocation]: ...

    def list_active_holds(
        self, *, scope: TenantScope, target: ScopedObjectRef
    ) -> Sequence[LegalHoldRecord]: ...

    def append_receipt(self, *, scope: TenantScope, receipt: DeletionReceipt) -> None: ...

    def complete_deletion_atomically(
        self,
        *,
        scope: TenantScope,
        job: DeletionJob,
        tombstone: TombstoneRecord,
    ) -> None:
        """Persist tombstone, final job state and outbox event in one transaction."""
        ...


class DenyAllReceiptVerifier:
    def verify(
        self,
        *,
        scope: TenantScope,
        command: DeletionReplicaCommand,
        receipt: DeletionReceipt,
    ) -> DeletionReceipt:
        del scope, command, receipt
        raise RuntimeError("deletion receipt verifier is not configured")
