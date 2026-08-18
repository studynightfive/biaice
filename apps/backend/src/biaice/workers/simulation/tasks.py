"""FR-06/07/08/09a Celery task registry.

The simulation queue (`simulation`) is pre-registered in
`biaice/worker.py`. The tasks in this module call into the
`SimulationWorkerRuntime` Protocol so that production deployments can wire a
real Python+NumPy evaluator while tests use the deterministic
`DefaultSimulationRuntime`.
"""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from biaice.worker import celery_app


class SimulationWorkerRuntime(Protocol):
    def run_batch(self, batch_id: UUID) -> dict[str, Any]: ...

    def run_optimization(self, run_id: UUID) -> dict[str, Any]: ...

    def assess_eligibility(self, eligibility_id: UUID) -> dict[str, Any]: ...

    def create_snapshot(self, snapshot_id: UUID) -> dict[str, Any]: ...


_runtime: SimulationWorkerRuntime | None = None


def bind_runtime(runtime: SimulationWorkerRuntime) -> None:
    global _runtime
    _runtime = runtime


def require_runtime() -> SimulationWorkerRuntime:
    if _runtime is None:
        raise RuntimeError(
            "simulation worker runtime is not configured; refusing to acknowledge work"
        )
    return _runtime


@celery_app.task(
    name="biaice.simulation.run_batch",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_batch(self, batch_id: str) -> dict[str, Any]:
    del self
    return require_runtime().run_batch(UUID(batch_id))


@celery_app.task(
    name="biaice.simulation.run_optimization",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_optimization(self, run_id: str) -> dict[str, Any]:
    del self
    return require_runtime().run_optimization(UUID(run_id))


@celery_app.task(
    name="biaice.simulation.assess_eligibility",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def assess_eligibility(self, eligibility_id: str) -> dict[str, Any]:
    del self
    return require_runtime().assess_eligibility(UUID(eligibility_id))


@celery_app.task(
    name="biaice.simulation.create_snapshot",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def create_snapshot(self, snapshot_id: str) -> dict[str, Any]:
    del self
    return require_runtime().create_snapshot(UUID(snapshot_id))
