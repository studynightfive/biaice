"""FR-02 FR-11 ReplicaDeletionAdapter for the member-3 local object store."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from biaice.core.auth import TenantScope
from biaice.core.clock import Clock, SystemClock
from biaice.modules.documents.application.ports import LegalHoldQueryPort, NoLegalHolds
from biaice.modules.documents.application.repository import InMemoryDocumentsRepository
from biaice.modules.governance.domain.models import (
    DeletionReceipt,
    DeletionReplicaCommand,
    ReceiptOutcome,
    ReplicaKind,
)

MEMBER3_ADAPTER_NAME = "member3-local"


class LocalReplicaDeletionAdapter:
    """Returns a receipt only. It never completes a DeletionJob."""

    ADAPTER_NAME = MEMBER3_ADAPTER_NAME

    def __init__(
        self,
        *,
        repository: InMemoryDocumentsRepository,
        legal_holds: LegalHoldQueryPort | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.repository = repository
        self.legal_holds = legal_holds or NoLegalHolds()
        self.clock = clock or SystemClock()

    @property
    def adapter_name(self) -> str:
        return self.ADAPTER_NAME

    @property
    def supported_kinds(self) -> frozenset[ReplicaKind]:
        return frozenset({ReplicaKind.OBJECT_STORAGE, ReplicaKind.TEMPORARY_FILE})

    def delete(
        self, *, scope: TenantScope, command: DeletionReplicaCommand
    ) -> DeletionReceipt:
        replica = command.replica
        now = self.clock.now()
        holds = self.legal_holds.list_active_holds(scope=scope, target=replica.target)
        if holds:
            return self._make_receipt(
                command=command,
                scope=scope,
                outcome=ReceiptOutcome.FAILED_TERMINAL,
                evidence_hash=hashlib.sha256(b"blocked-by-legal-hold").hexdigest(),
                completed_at=now,
                stable_error_code="DELETION_BLOCKED_BY_LEGAL_HOLD",
            )
        key = self.repository.key_for_locator(replica.locator_hash)
        if key is None or not self.repository.blob_exists(key):
            return self._make_receipt(
                command=command,
                scope=scope,
                outcome=ReceiptOutcome.SUCCEEDED,
                evidence_hash=hashlib.sha256(b"already-deleted").hexdigest(),
                completed_at=now,
            )
        self.repository.delete_blob(key)
        if self.repository.blob_exists(key):
            return self._make_receipt(
                command=command,
                scope=scope,
                outcome=ReceiptOutcome.FAILED_RETRYABLE,
                evidence_hash=hashlib.sha256(b"deletion-verification-failed").hexdigest(),
                completed_at=now,
                stable_error_code="STORAGE_DELETE_FAILED",
                retry_after=now + timedelta(hours=1),
            )
        evidence_hash = hashlib.sha256(
            f"deleted:{key}:{replica.locator_hash}:{now.isoformat()}".encode()
        ).hexdigest()
        return self._make_receipt(
            command=command,
            scope=scope,
            outcome=ReceiptOutcome.SUCCEEDED,
            evidence_hash=evidence_hash,
            completed_at=now,
        )

    def _make_receipt(
        self,
        *,
        command: DeletionReplicaCommand,
        scope: TenantScope,
        outcome: ReceiptOutcome,
        evidence_hash: str,
        completed_at: datetime,
        stable_error_code: str | None = None,
        retry_after: datetime | None = None,
    ) -> DeletionReceipt:
        signature_input = (
            f"{command.command_id}:{command.replica.replica_id}:"
            f"{outcome.value}:{evidence_hash}:{completed_at.isoformat()}"
        )
        adapter_signature = hashlib.sha256(signature_input.encode()).hexdigest()
        return DeletionReceipt(
            receipt_id=uuid4(),
            deletion_job_id=command.deletion_job_id,
            replica_id=command.replica.replica_id,
            tenant_id=scope.tenant_id,
            data_domain_id=scope.data_domain_id,
            adapter_name=self.adapter_name,
            outcome=outcome,
            attempted_at=command.issued_at,
            completed_at=completed_at,
            evidence_hash=evidence_hash,
            adapter_signature=adapter_signature,
            verified=False,
            stable_error_code=stable_error_code,
            retry_after=retry_after,
        )
