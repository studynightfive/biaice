"""Simulation assessment snapshot creation with SHADOW_PILOT_LOCKED watermark.

The snapshot is the immutable evidence package consumed by the recommendation
eligibility assessor and by the auditor. It always carries the
SHADOW_PILOT_LOCKED watermark to make absolutely clear that the snapshot is
not a real-money / real-API-key / real-pilot binding artefact.

The payload hash is computed over the canonical JSON projection; the caller
must therefore never mutate the payload after creation. The create_snapshot
helper also refuses to produce a snapshot whose payload hash would not match
the committed version, surfacing SNAPSHOT_PAYLOAD_HASH_MISMATCH.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    SHADOW_PILOT_LOCKED_WATERMARK,
    ReviewValidity,
    SnapshotState,
    SimulationAssessmentSnapshot,
    new_uuid,
)


def canonical_payload(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def compute_payload_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class SnapshotRequest:
    snapshot_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None
    decision_unit_id: UUID
    payload: Mapping[str, Any]
    created_at: datetime
    created_by: UUID
    lock: bool = True


def create_snapshot(request: SnapshotRequest) -> SimulationAssessmentSnapshot:
    """Build and lock a SHADOW_PILOT_LOCKED snapshot; verify payload hash round-trip."""
    if not request.payload:
        raise BiaiceError(
            "SNAPSHOT_PAYLOAD_HASH_MISMATCH",
            detail=(
                "快照 payload 不能为空 / Snapshot payload cannot be empty."
            ),
        )
    payload_hash = compute_payload_hash(request.payload)
    snapshot = SimulationAssessmentSnapshot(
        snapshot_id=request.snapshot_id,
        version_id=request.version_id,
        tenant_id=request.tenant_id,
        data_domain_id=request.data_domain_id,
        project_id=request.project_id,
        decision_unit_id=request.decision_unit_id,
        state=SnapshotState.LOCKED if request.lock else SnapshotState.DRAFT,
        watermark=SHADOW_PILOT_LOCKED_WATERMARK,
        payload_hash=payload_hash,
        payload=dict(request.payload),
        created_at=request.created_at,
        created_by=request.created_by,
        locked_at=request.created_at if request.lock else None,
        locked_by=request.created_by if request.lock else None,
    )
    if snapshot.payload_hash != compute_payload_hash(snapshot.payload):
        raise BiaiceError(
            "SNAPSHOT_PAYLOAD_HASH_MISMATCH",
            detail=(
                "快照 payload hash 在序列化后不再匹配 / Snapshot payload hash no longer "
                "matches after serialisation; refusing to publish the snapshot."
            ),
        )
    return snapshot


def assert_shadow_watermark(snapshot: SimulationAssessmentSnapshot) -> None:
    if snapshot.watermark != SHADOW_PILOT_LOCKED_WATERMARK:
        raise BiaiceError(
            "SNAPSHOT_PAYLOAD_HASH_MISMATCH",
            detail=(
                "快照必须携带 SHADOW_PILOT_LOCKED 水印 / Snapshot must carry the "
                f"SHADOW_PILOT_LOCKED watermark; received {snapshot.watermark!r}."
            ),
        )
