"""Deterministic in-memory runtime used by the simulation worker.

Production deployments wire a real numpy/pandas evaluator into the same
Protocol; the default implementation here exists so unit tests, the contract
test, and the worker smoke can run without external services.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from biaice.core.clock import Clock, SystemClock
from biaice.modules.simulation.application.repository import InMemorySimulationRepository
from biaice.modules.simulation.domain.models import (
    BatchState,
    OptimizationState,
    SHADOW_PILOT_LOCKED_WATERMARK,
    SnapshotState,
)
from biaice.modules.simulation.domain.snapshot import compute_payload_hash


class DefaultSimulationRuntime:
    """Deterministic in-memory runtime for FR-06/07/08/09a Celery tasks."""

    def __init__(
        self,
        repository: InMemorySimulationRepository,
        clock: Clock | None = None,
    ) -> None:
        self.repository = repository
        self.clock = clock or SystemClock()

    def run_batch(self, batch_id: UUID) -> dict[str, Any]:
        batches = self.repository._batches  # type: ignore[attr-defined]
        match = batches.get(batch_id)
        if match is None:
            return {"batch_id": str(batch_id), "state": BatchState.FAILED_TERMINAL.value}
        updated = match.model_copy(update={"state": BatchState.SUCCEEDED, "last_updated_at": self.clock.now()})
        self.repository.upsert_batch(updated)
        return {"batch_id": str(updated.batch_id), "state": updated.state.value}

    def run_optimization(self, run_id: UUID) -> dict[str, Any]:
        runs = self.repository._optimization_runs  # type: ignore[attr-defined]
        match = runs.get(run_id)
        if match is None:
            return {"run_id": str(run_id), "state": OptimizationState.FAILED.value}
        updated = match.model_copy(update={"state": OptimizationState.SUCCEEDED, "finalized_at": self.clock.now()})
        self.repository.upsert_optimization_run(updated)
        return {"run_id": str(updated.run_id), "state": updated.state.value}

    def assess_eligibility(self, eligibility_id: UUID) -> dict[str, Any]:
        items = self.repository._recommendation_eligibilities  # type: ignore[attr-defined]
        match = items.get(eligibility_id)
        if match is None:
            return {"eligibility_id": str(eligibility_id), "state": "UNKNOWN"}
        return {
            "eligibility_id": str(match.eligibility_id),
            "state": match.state.value,
            "blocked_reason_codes": list(match.blocked_reason_codes),
        }

    def create_snapshot(self, snapshot_id: UUID) -> dict[str, Any]:
        items = self.repository._snapshots  # type: ignore[attr-defined]
        match = items.get(snapshot_id)
        if match is None:
            return {"snapshot_id": str(snapshot_id), "state": SnapshotState.DRAFT.value}
        verify_hash = compute_payload_hash(match.payload)
        if verify_hash != match.payload_hash or match.watermark != SHADOW_PILOT_LOCKED_WATERMARK:
            return {
                "snapshot_id": str(match.snapshot_id),
                "state": SnapshotState.DRAFT.value,
                "watermark": match.watermark,
            }
        locked = match.model_copy(update={"state": SnapshotState.LOCKED, "locked_at": self.clock.now()})
        self.repository.upsert_snapshot(locked)
        return {"snapshot_id": str(locked.snapshot_id), "state": locked.state.value}
