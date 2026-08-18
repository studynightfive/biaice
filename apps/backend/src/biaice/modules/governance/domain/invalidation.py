"""Idempotent event × dependency invalidation matrix."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Iterable
from uuid import UUID, uuid4

from biaice.modules.governance.domain.models import (
    DataLineageEdge,
    DependencyType,
    InvalidationEffect,
    InvalidationEvent,
    UpstreamChangeType,
)

INVALIDATION_MATRIX: dict[UpstreamChangeType, dict[DependencyType, InvalidationEffect]] = {
    UpstreamChangeType.DRAFT_CREATED: {},
    UpstreamChangeType.SNAPSHOT_FROZEN: {},
    UpstreamChangeType.PUBLISH_EFFECTIVE: {
        kind: InvalidationEffect.STALE for kind in DependencyType
    },
    UpstreamChangeType.REVOKE: {kind: InvalidationEffect.INVALIDATED for kind in DependencyType},
    UpstreamChangeType.DELETE: {kind: InvalidationEffect.INVALIDATED for kind in DependencyType},
    UpstreamChangeType.RETENTION_EXPIRED: {
        kind: InvalidationEffect.INVALIDATED for kind in DependencyType
    },
    UpstreamChangeType.AUTHORIZATION_WITHDRAWN: {
        DependencyType.AUTHORIZATION: InvalidationEffect.INVALIDATED,
    },
    UpstreamChangeType.PURPOSE_ENDED: {
        DependencyType.AUTHORIZATION: InvalidationEffect.INVALIDATED,
    },
    UpstreamChangeType.PROVIDER_POLICY_EXPIRED: {
        DependencyType.POLICY: InvalidationEffect.INVALIDATED,
        DependencyType.AUTHORIZATION: InvalidationEffect.INVALIDATED,
    },
    UpstreamChangeType.MODEL_POLICY_EFFECTIVE: {
        DependencyType.POLICY: InvalidationEffect.STALE,
        DependencyType.COMPUTATIONAL: InvalidationEffect.STALE,
    },
}


def propagate_change(
    *,
    source_event_id: UUID,
    change_type: UpstreamChangeType,
    edges: Iterable[DataLineageEdge],
    changed_fields: frozenset[str],
    occurred_at: datetime,
) -> tuple[InvalidationEvent, ...]:
    """Return only actual, field-relevant downstream invalidations.

    The fingerprint makes repeated delivery safe at the repository unique-key
    boundary. Draft creation and snapshot freezing intentionally emit nothing.
    """

    effects = INVALIDATION_MATRIX[change_type]
    events: list[InvalidationEvent] = []
    for edge in edges:
        effect = effects.get(edge.dependency_type)
        if effect is None:
            continue
        if changed_fields and edge.affected_fields.isdisjoint(changed_fields):
            continue
        fingerprint = hashlib.sha256(
            f"{source_event_id}:{edge.edge_id}:{effect.value}".encode("utf-8")
        ).hexdigest()
        events.append(
            InvalidationEvent(
                invalidation_id=uuid4(),
                tenant_id=edge.tenant_id,
                data_domain_id=edge.data_domain_id,
                source_event_id=source_event_id,
                lineage_edge_id=edge.edge_id,
                downstream_type=edge.downstream_type,
                downstream_id=edge.downstream_id,
                downstream_version_id=edge.downstream_version_id,
                effect=effect,
                reason_code=f"UPSTREAM_{change_type.value}",
                occurred_at=occurred_at,
                idempotency_fingerprint=fingerprint,
            )
        )
    return tuple(events)
