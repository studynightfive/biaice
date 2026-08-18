"""Fail-closed, idempotent all-replica deletion coordinator."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from uuid import UUID, uuid4

from biaice.core.auth import IdentityContext, TenantScope
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.modules.governance.application.ports import (
    DeletionReceiptVerifier,
    GovernanceRepository,
    ReplicaDeletionAdapter,
)
from biaice.modules.governance.domain.models import (
    DeletionJob,
    DeletionJobState,
    DeletionReceipt,
    DeletionReplicaCommand,
    ReceiptOutcome,
    ScopedObjectRef,
    TombstoneRecord,
)


class DeletionCoordinator:
    def __init__(
        self,
        *,
        repository: GovernanceRepository,
        adapters: tuple[ReplicaDeletionAdapter, ...],
        receipt_verifier: DeletionReceiptVerifier,
        clock: Clock | None = None,
    ) -> None:
        self.repository = repository
        self.adapters = {adapter.adapter_name: adapter for adapter in adapters}
        self.receipt_verifier = receipt_verifier
        self.clock = clock or SystemClock()

    def request(
        self,
        *,
        identity: IdentityContext,
        target: ScopedObjectRef,
        reason_code: str,
        idempotency_key: str,
    ) -> DeletionJob:
        identity.scope.assert_allows(
            tenant_id=target.tenant_id,
            data_domain_id=target.data_domain_id,
            project_id=target.project_id,
            decision_unit_id=target.decision_unit_id,
        )
        # Repository must block logical access in the same transaction that
        # creates/deduplicates the job. Physical work is always later.
        job = self.repository.create_deletion_and_block_access(
            scope=identity.scope,
            target=target,
            requested_by=identity.subject_id,
            reason_code=reason_code,
            idempotency_key=idempotency_key,
        )
        if job.logical_access_blocked_at is None:
            raise RuntimeError("repository violated create-and-block atomicity")
        return job

    def run_once(self, *, scope: TenantScope, deletion_job_id: UUID) -> DeletionJob:
        job = self.repository.lock_deletion_job(scope=scope, deletion_job_id=deletion_job_id)
        if job is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        scope.assert_allows(
            tenant_id=job.target.tenant_id,
            data_domain_id=job.target.data_domain_id,
            project_id=job.target.project_id,
            decision_unit_id=job.target.decision_unit_id,
        )
        if job.state == DeletionJobState.COMPLETED:
            return job
        if job.logical_access_blocked_at is None:
            raise RuntimeError("physical deletion cannot precede logical access blocking")

        holds = self.repository.list_active_holds(scope=scope, target=job.target)
        if holds:
            blocked = job.model_copy(
                update={
                    "state": DeletionJobState.WAITING_FOR_HOLD_RELEASE,
                    "legal_hold_count": len(holds),
                }
            )
            self.repository.save_deletion_job(scope=scope, job=blocked)
            return blocked

        replicas = tuple(self.repository.list_replicas(scope=scope, target=job.target))
        required_replica_ids = frozenset(
            replica.replica_id for replica in replicas if replica.required_for_completion
        )
        if not required_replica_ids:
            # Registry completeness is part of the deletion proof. An empty
            # required set is UNKNOWN, never vacuous success.
            escalated = job.model_copy(
                update={
                    "state": DeletionJobState.ESCALATED,
                    "legal_hold_count": 0,
                    "attempt": job.attempt + 1,
                }
            )
            self.repository.save_deletion_job(scope=scope, job=escalated)
            return escalated
        existing_by_replica = {receipt.replica_id: receipt for receipt in job.receipts}
        all_receipts: list[DeletionReceipt] = list(job.receipts)
        attempted = job.model_copy(
            update={
                "state": DeletionJobState.DISPATCHING,
                "required_replica_ids": required_replica_ids,
                "legal_hold_count": 0,
                "attempt": job.attempt + 1,
            }
        )
        self.repository.save_deletion_job(scope=scope, job=attempted)

        for replica in replicas:
            prior = existing_by_replica.get(replica.replica_id)
            if prior is not None and prior.satisfies_completion:
                continue
            adapter = self.adapters.get(replica.adapter_name)
            if adapter is None or replica.kind not in adapter.supported_kinds:
                # A required unknown adapter can never be silently skipped.
                unsupported = DeletionReceipt(
                    receipt_id=uuid4(),
                    deletion_job_id=job.deletion_job_id,
                    replica_id=replica.replica_id,
                    tenant_id=scope.tenant_id,
                    data_domain_id=scope.data_domain_id,
                    adapter_name=replica.adapter_name,
                    outcome=ReceiptOutcome.UNSUPPORTED,
                    attempted_at=self.clock.now(),
                    evidence_hash=hashlib.sha256(b"adapter-unavailable").hexdigest(),
                    adapter_signature="UNVERIFIED",
                    verified=False,
                    stable_error_code="DELETION_ADAPTER_UNAVAILABLE",
                )
                self.repository.append_receipt(scope=scope, receipt=unsupported)
                all_receipts.append(unsupported)
                continue
            command = DeletionReplicaCommand(
                command_id=uuid4(),
                deletion_job_id=job.deletion_job_id,
                replica=replica,
                issued_at=self.clock.now(),
                deadline_at=self.clock.now() + timedelta(seconds=replica.deletion_sla_seconds),
                attempt=attempted.attempt,
                idempotency_key=f"{job.deletion_job_id}:{replica.replica_id}",
            )
            raw_receipt = adapter.delete(scope=scope, command=command)
            self._assert_receipt_binding(scope=scope, job=job, command=command, receipt=raw_receipt)
            receipt = self.receipt_verifier.verify(
                scope=scope, command=command, receipt=raw_receipt
            )
            self._assert_receipt_binding(scope=scope, job=job, command=command, receipt=receipt)
            self.repository.append_receipt(scope=scope, receipt=receipt)
            all_receipts.append(receipt)

        latest_by_replica = {receipt.replica_id: receipt for receipt in all_receipts}
        successful_ids = {
            replica_id
            for replica_id, receipt in latest_by_replica.items()
            if receipt.satisfies_completion
        }
        if not required_replica_ids.issubset(successful_ids):
            failed = any(
                receipt.outcome in {ReceiptOutcome.FAILED_TERMINAL, ReceiptOutcome.UNSUPPORTED}
                for receipt in latest_by_replica.values()
            )
            waiting = attempted.model_copy(
                update={
                    "state": DeletionJobState.ESCALATED
                    if failed
                    else DeletionJobState.PARTIALLY_FAILED,
                    "receipts": tuple(latest_by_replica.values()),
                }
            )
            self.repository.save_deletion_job(scope=scope, job=waiting)
            return waiting

        completed_at = self.clock.now()
        tombstone = TombstoneRecord(
            tombstone_id=uuid4(),
            tenant_id=scope.tenant_id,
            data_domain_id=scope.data_domain_id,
            deleted_object_type=job.target.object_type,
            deleted_object_id=job.target.object_id,
            deleted_version_id=job.target.version_id,
            deletion_job_id=job.deletion_job_id,
            deleted_at=completed_at,
            reason_code=job.reason_code,
            minimal_reference_hash=hashlib.sha256(
                f"{job.target.object_type}:{job.target.object_id}:{job.target.version_id or ''}".encode(
                    "utf-8"
                )
            ).hexdigest(),
        )
        completed = DeletionJob.model_validate(
            {
                **attempted.model_dump(),
                "state": DeletionJobState.COMPLETED,
                "receipts": tuple(latest_by_replica.values()),
                "completed_at": completed_at,
                "tombstone_id": tombstone.tombstone_id,
            }
        )
        # Repository implementation must persist tombstone, final state and
        # outbox event atomically. The event is never emitted before receipts.
        self.repository.complete_deletion_atomically(
            scope=scope, job=completed, tombstone=tombstone
        )
        return completed

    @staticmethod
    def _assert_receipt_binding(
        *,
        scope: TenantScope,
        job: DeletionJob,
        command: DeletionReplicaCommand,
        receipt: DeletionReceipt,
    ) -> None:
        if (
            receipt.deletion_job_id != job.deletion_job_id
            or receipt.replica_id != command.replica.replica_id
            or receipt.tenant_id != scope.tenant_id
            or receipt.data_domain_id != scope.data_domain_id
            or receipt.adapter_name != command.replica.adapter_name
        ):
            raise BiaiceError("DELETION_RECEIPT_INVALID")
