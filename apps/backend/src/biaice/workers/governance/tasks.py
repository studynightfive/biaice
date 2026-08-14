"""Governance task registry; durable truth and idempotency remain PostgreSQL."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from biaice.worker import celery_app


class GovernanceWorkerRuntime(Protocol):
    def process_deletion(self, deletion_job_id: UUID) -> None: ...

    def process_retention_due(self) -> None: ...

    def reconcile_outbox(self) -> None: ...

    def replay_tombstones(self) -> None: ...


_runtime: GovernanceWorkerRuntime | None = None


def bind_runtime(runtime: GovernanceWorkerRuntime) -> None:
    global _runtime
    _runtime = runtime


def require_runtime() -> GovernanceWorkerRuntime:
    if _runtime is None:
        raise RuntimeError(
            "governance worker runtime is not configured; refusing to acknowledge work"
        )
    return _runtime


@celery_app.task(
    name="biaice.governance.process_deletion",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_deletion(self, deletion_job_id: str) -> None:
    del self
    require_runtime().process_deletion(UUID(deletion_job_id))


@celery_app.task(
    name="biaice.governance.process_retention_due",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def process_retention_due(self) -> None:
    del self
    require_runtime().process_retention_due()


@celery_app.task(
    name="biaice.governance.reconcile_outbox",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def reconcile_outbox(self) -> None:
    del self
    require_runtime().reconcile_outbox()


@celery_app.task(name="biaice.governance.replay_tombstones", bind=True, max_retries=0)
def replay_tombstones(self) -> None:
    del self
    require_runtime().replay_tombstones()
