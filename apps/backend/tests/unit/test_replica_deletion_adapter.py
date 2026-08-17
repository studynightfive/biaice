"""Unit tests for the member-3 local replica deletion adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from biaice.core.auth import TenantScope
from biaice.modules.documents.application.ports import InMemoryLegalHoldQuery
from biaice.modules.documents.application.repository import InMemoryDocumentsRepository
from biaice.modules.documents.infrastructure.deletion_adapters.local_storage import (
    MEMBER3_ADAPTER_NAME,
    LocalReplicaDeletionAdapter,
)
from biaice.modules.governance.domain.models import (
    AdapterOwner,
    DeletionReplicaCommand,
    LegalHoldRecord,
    LegalHoldState,
    ReceiptOutcome,
    ReplicaKind,
    ReplicaLocation,
    ScopedObjectRef,
)

NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
TENANT = uuid4()
DOMAIN = uuid4()


class FixedClock:
    def now(self) -> datetime:
        return NOW


def _scope() -> TenantScope:
    return TenantScope(
        tenant_id=TENANT,
        data_domain_id=DOMAIN,
        all_projects=True,
        all_decision_units=True,
    )


def _command(replica: ReplicaLocation) -> DeletionReplicaCommand:
    return DeletionReplicaCommand(
        command_id=uuid4(),
        deletion_job_id=uuid4(),
        replica=replica,
        issued_at=NOW,
        deadline_at=NOW,
        attempt=1,
        idempotency_key="delete-replica-test-key",
    )


def test_adapter_deletes_blob_and_never_completes_a_job() -> None:
    repository = InMemoryDocumentsRepository()
    key = "quarantine/doc.bin"
    locator = repository.put_blob(key, b"%PDF-1.4\n")
    replica = ReplicaLocation(
        replica_id=uuid4(),
        target=ScopedObjectRef(
            tenant_id=TENANT,
            data_domain_id=DOMAIN,
            object_type="SourceDocument",
            object_id=uuid4(),
        ),
        kind=ReplicaKind.OBJECT_STORAGE,
        adapter_name=MEMBER3_ADAPTER_NAME,
        adapter_owner=AdapterOwner.MEMBER_3_LOCAL_REPLICA,
        locator_hash=locator,
        deletion_sla_seconds=3600,
    )
    adapter = LocalReplicaDeletionAdapter(repository=repository, clock=FixedClock())
    receipt = adapter.delete(scope=_scope(), command=_command(replica))
    assert receipt.outcome is ReceiptOutcome.SUCCEEDED
    assert receipt.adapter_name == MEMBER3_ADAPTER_NAME
    assert not repository.blob_exists(key)


def test_adapter_returns_blocked_receipt_when_legal_hold_is_active() -> None:
    repository = InMemoryDocumentsRepository()
    key = "quarantine/held.bin"
    locator = repository.put_blob(key, b"%PDF-1.4\n")
    target = ScopedObjectRef(
        tenant_id=TENANT,
        data_domain_id=DOMAIN,
        object_type="SourceDocument",
        object_id=uuid4(),
    )
    replica = ReplicaLocation(
        replica_id=uuid4(),
        target=target,
        kind=ReplicaKind.OBJECT_STORAGE,
        adapter_name=MEMBER3_ADAPTER_NAME,
        adapter_owner=AdapterOwner.MEMBER_3_LOCAL_REPLICA,
        locator_hash=locator,
        deletion_sla_seconds=3600,
    )
    holds = InMemoryLegalHoldQuery(
        (
            LegalHoldRecord(
                legal_hold_id=uuid4(),
                target=target,
                state=LegalHoldState.ACTIVE,
                reason_code="LITIGATION",
                authority_reference_hash=hashlib.sha256(b"hold").hexdigest(),
                placed_by=uuid4(),
                placed_at=NOW,
            ),
        )
    )
    adapter = LocalReplicaDeletionAdapter(
        repository=repository, legal_holds=holds, clock=FixedClock()
    )
    receipt = adapter.delete(scope=_scope(), command=_command(replica))
    assert receipt.outcome is ReceiptOutcome.FAILED_TERMINAL
    assert receipt.stable_error_code == "DELETION_BLOCKED_BY_LEGAL_HOLD"
    assert repository.blob_exists(key)
