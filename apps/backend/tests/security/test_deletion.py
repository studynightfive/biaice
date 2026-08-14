from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from conftest import DOMAIN_A, TENANT_A, TENANT_B
from pydantic import ValidationError

from biaice.modules.governance.application.deletion import DeletionCoordinator
from biaice.modules.governance.domain.models import (
    AdapterOwner,
    DeletionJob,
    DeletionJobState,
    DeletionReceipt,
    LegalHoldRecord,
    LegalHoldState,
    ReceiptOutcome,
    ReplicaKind,
    ReplicaLocation,
    ScopedObjectRef,
    TombstoneRecord,
)

NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FakeRepository:
    def __init__(
        self,
        replicas: tuple[ReplicaLocation, ...],
        holds: tuple[LegalHoldRecord, ...] = (),
    ) -> None:
        self.replicas = replicas
        self.holds = holds
        self.job: DeletionJob | None = None
        self.receipts: list[DeletionReceipt] = []
        self.tombstone: TombstoneRecord | None = None
        self.completed_event_count = 0

    def create_deletion_and_block_access(
        self, *, scope, target, requested_by, reason_code, idempotency_key
    ):
        if self.job is None:
            self.job = DeletionJob(
                deletion_job_id=uuid4(),
                target=target,
                state=DeletionJobState.LOGICAL_ACCESS_BLOCKED,
                reason_code=reason_code,
                requested_by=requested_by,
                requested_at=NOW,
                idempotency_key=idempotency_key,
                logical_access_blocked_at=NOW,
            )
        return self.job

    def lock_deletion_job(self, *, scope, deletion_job_id):
        assert self.job is None or self.job.deletion_job_id == deletion_job_id
        return self.job

    def save_deletion_job(self, *, scope, job):
        self.job = job

    def list_replicas(self, *, scope, target):
        return self.replicas

    def list_active_holds(self, *, scope, target):
        return self.holds

    def append_receipt(self, *, scope, receipt):
        self.receipts.append(receipt)

    def complete_deletion_atomically(self, *, scope, job, tombstone):
        assert job.state == DeletionJobState.COMPLETED
        self.job = job
        self.tombstone = tombstone
        self.completed_event_count += 1


class Adapter:
    def __init__(self, name: str, kind: ReplicaKind, outcome: ReceiptOutcome) -> None:
        self._name = name
        self._kinds = frozenset({kind})
        self.outcome = outcome
        self.calls = 0

    @property
    def adapter_name(self):
        return self._name

    @property
    def supported_kinds(self):
        return self._kinds

    def delete(self, *, scope, command):
        self.calls += 1
        return DeletionReceipt(
            receipt_id=uuid4(),
            deletion_job_id=command.deletion_job_id,
            replica_id=command.replica.replica_id,
            tenant_id=scope.tenant_id,
            data_domain_id=scope.data_domain_id,
            adapter_name=self.adapter_name,
            outcome=self.outcome,
            attempted_at=NOW,
            completed_at=NOW if self.outcome == ReceiptOutcome.SUCCEEDED else None,
            evidence_hash=hashlib.sha256(
                f"{self.adapter_name}:{self.outcome}".encode()
            ).hexdigest(),
            adapter_signature="test-signature",
            verified=False,
            stable_error_code=None
            if self.outcome == ReceiptOutcome.SUCCEEDED
            else "TEST_FAILURE",
        )


class Verifier:
    def verify(self, *, scope, command, receipt):
        return receipt.model_copy(update={"verified": True})


def replica(name: str, kind: ReplicaKind, owner: AdapterOwner) -> ReplicaLocation:
    target = ScopedObjectRef(
        tenant_id=TENANT_A,
        data_domain_id=DOMAIN_A,
        object_type="SourceDocumentVersion",
        object_id=UUID("00000000-0000-4000-8000-000000000099"),
    )
    return ReplicaLocation(
        replica_id=uuid4(),
        target=target,
        kind=kind,
        adapter_name=name,
        adapter_owner=owner,
        locator_hash=hashlib.sha256(name.encode()).hexdigest(),
        deletion_sla_seconds=3600,
    )


def setup_coordinator(identity, provider_outcome=ReceiptOutcome.SUCCEEDED, holds=()):
    local_replica = replica(
        "member3-local", ReplicaKind.OBJECT_STORAGE, AdapterOwner.MEMBER_3_LOCAL_REPLICA
    )
    provider_replica = replica(
        "member5-provider",
        ReplicaKind.PROVIDER_EXTERNAL,
        AdapterOwner.MEMBER_5_PROVIDER_REPLICA,
    )
    repository = FakeRepository((local_replica, provider_replica), holds=holds)
    local = Adapter(
        "member3-local", ReplicaKind.OBJECT_STORAGE, ReceiptOutcome.SUCCEEDED
    )
    provider = Adapter(
        "member5-provider", ReplicaKind.PROVIDER_EXTERNAL, provider_outcome
    )
    coordinator = DeletionCoordinator(
        repository=repository,
        adapters=(local, provider),
        receipt_verifier=Verifier(),
        clock=FixedClock(),
    )
    job = coordinator.request(
        identity=identity,
        target=local_replica.target,
        reason_code="DATA_SUBJECT_REQUEST",
        idempotency_key="deletion-request-0001",
    )
    return coordinator, repository, local, provider, job


def test_deletion_never_completes_until_local_and_provider_receipts_succeed(
    identity,
) -> None:
    coordinator, repository, _, _, job = setup_coordinator(
        identity, ReceiptOutcome.FAILED_RETRYABLE
    )
    result = coordinator.run_once(
        scope=identity.scope, deletion_job_id=job.deletion_job_id
    )
    assert result.state == DeletionJobState.PARTIALLY_FAILED
    assert repository.completed_event_count == 0
    assert repository.tombstone is None


def test_deletion_completes_atomically_after_all_verified_receipts(identity) -> None:
    coordinator, repository, local, provider, job = setup_coordinator(identity)
    result = coordinator.run_once(
        scope=identity.scope, deletion_job_id=job.deletion_job_id
    )
    assert result.state == DeletionJobState.COMPLETED
    assert local.calls == provider.calls == 1
    assert repository.tombstone is not None
    assert repository.completed_event_count == 1
    assert len(result.receipts) == 2


def test_legal_hold_delays_physical_deletion_but_logical_access_stays_blocked(
    identity,
) -> None:
    target = ScopedObjectRef(
        tenant_id=TENANT_A,
        data_domain_id=DOMAIN_A,
        object_type="SourceDocumentVersion",
        object_id=UUID("00000000-0000-4000-8000-000000000099"),
    )
    hold = LegalHoldRecord(
        legal_hold_id=uuid4(),
        target=target,
        state=LegalHoldState.ACTIVE,
        reason_code="LITIGATION",
        authority_reference_hash=hashlib.sha256(b"authority").hexdigest(),
        placed_by=identity.subject_id,
        placed_at=NOW,
    )
    coordinator, repository, local, provider, job = setup_coordinator(
        identity, holds=(hold,)
    )
    result = coordinator.run_once(
        scope=identity.scope, deletion_job_id=job.deletion_job_id
    )
    assert result.state == DeletionJobState.WAITING_FOR_HOLD_RELEASE
    assert result.logical_access_blocked_at == NOW
    assert local.calls == provider.calls == 0
    assert repository.completed_event_count == 0


def test_empty_replica_registry_is_unknown_not_vacuous_success(identity) -> None:
    repository = FakeRepository(())
    coordinator = DeletionCoordinator(
        repository=repository,
        adapters=(),
        receipt_verifier=Verifier(),
        clock=FixedClock(),
    )
    target = ScopedObjectRef(
        tenant_id=TENANT_A,
        data_domain_id=DOMAIN_A,
        object_type="DerivedDataAssetVersion",
        object_id=uuid4(),
    )
    job = coordinator.request(
        identity=identity,
        target=target,
        reason_code="RETENTION_EXPIRED",
        idempotency_key="empty-registry-0001",
    )
    result = coordinator.run_once(
        scope=identity.scope, deletion_job_id=job.deletion_job_id
    )
    assert result.state == DeletionJobState.ESCALATED
    assert repository.completed_event_count == 0


def test_completed_domain_object_rejects_missing_receipts(identity) -> None:
    with pytest.raises(ValidationError):
        DeletionJob(
            deletion_job_id=uuid4(),
            target=ScopedObjectRef(
                tenant_id=TENANT_A,
                data_domain_id=DOMAIN_A,
                object_type="SourceDocumentVersion",
                object_id=uuid4(),
            ),
            state=DeletionJobState.COMPLETED,
            reason_code="TEST",
            requested_by=identity.subject_id,
            requested_at=NOW,
            idempotency_key="invalid-completed-1",
            logical_access_blocked_at=NOW,
            required_replica_ids=frozenset({uuid4()}),
            receipts=(),
            completed_at=NOW,
            tombstone_id=uuid4(),
        )


def test_cross_tenant_deletion_target_is_rejected(identity) -> None:
    repository = FakeRepository(())
    coordinator = DeletionCoordinator(
        repository=repository,
        adapters=(),
        receipt_verifier=Verifier(),
        clock=FixedClock(),
    )
    target = ScopedObjectRef(
        tenant_id=TENANT_B,
        data_domain_id=DOMAIN_A,
        object_type="SourceDocumentVersion",
        object_id=uuid4(),
    )
    with pytest.raises(Exception) as error:
        coordinator.request(
            identity=identity,
            target=target,
            reason_code="TEST",
            idempotency_key="cross-tenant-0001",
        )
    assert getattr(error.value, "code", None) == "TENANT_SCOPE_VIOLATION"
