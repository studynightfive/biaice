"""FR-06/07/08/09a simulation application services — orchestration, audit, outbox, jobs.

Composition root rules:
    * services are stateless except for injected ports (audit, outbox, clock, job);
    * the in-memory repository is the only state holder; SQLAlchemy adapter is
      deferred to a follow-up PR per the M0 split;
    * every write action emits an AuditEvent and an OutboxEventRecord when the
      aggregate is committed.
"""
from biaice.modules.simulation.application.repository import InMemorySimulationRepository
from biaice.modules.simulation.application.services import (
    BaselineService,
    EligibilityService,
    OptimizationService,
    ScenarioSetService,
    SearchSpaceService,
    SimulationBatchService,
    SnapshotService,
    configure_simulation,
)

__all__ = [
    "BaselineService",
    "EligibilityService",
    "InMemorySimulationRepository",
    "OptimizationService",
    "ScenarioSetService",
    "SearchSpaceService",
    "SimulationBatchService",
    "SnapshotService",
    "configure_simulation",
]
