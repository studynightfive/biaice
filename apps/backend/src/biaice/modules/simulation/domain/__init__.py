"""FR-06/07/08/09a simulation domain — pure functions, frozen models, deterministic referees.

Layering rules (per M0 architecture):
    * domain modules never import from application/, api/ or workers/;
    * application services compose domain helpers and use the in-memory repository;
    * API and worker layers never re-implement referee/probability logic;
    * cross-tenant access and MFA must be enforced above this layer.
"""
from biaice.modules.simulation.domain import (
    eligibility,
    manifest,
    merge,
    models,
    optimization,
    probability,
    referee,
    scenarios,
    snapshot,
    static_validation,
    stress,
)

__all__ = [
    "eligibility",
    "manifest",
    "merge",
    "models",
    "optimization",
    "probability",
    "referee",
    "scenarios",
    "snapshot",
    "static_validation",
    "stress",
]
