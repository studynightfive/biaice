from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from conftest import DOMAIN_A, TENANT_A

from biaice.modules.governance.application.retention import evaluate_retention_expiry
from biaice.modules.governance.domain.invalidation import propagate_change
from biaice.modules.governance.domain.models import (
    DataLineageEdge,
    DependencyType,
    InvalidationEffect,
    RetentionAction,
    RetentionDispositionJob,
    RetentionJobState,
    ScopedObjectRef,
    UpstreamChangeType,
)


def edge(
    dependency_type: DependencyType, affected_fields: frozenset[str]
) -> DataLineageEdge:
    return DataLineageEdge(
        edge_id=uuid4(),
        tenant_id=TENANT_A,
        data_domain_id=DOMAIN_A,
        upstream_type="RuleSetVersion",
        upstream_id=uuid4(),
        upstream_version_id=uuid4(),
        downstream_type="PrecheckAssessmentVersion",
        downstream_id=uuid4(),
        dependency_type=dependency_type,
        affected_fields=affected_fields,
        created_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


def test_draft_and_snapshot_freeze_do_not_propagate() -> None:
    lineage = [edge(DependencyType.COMPUTATIONAL, frozenset({"formula"}))]
    for change in (
        UpstreamChangeType.DRAFT_CREATED,
        UpstreamChangeType.SNAPSHOT_FROZEN,
    ):
        assert (
            propagate_change(
                source_event_id=uuid4(),
                change_type=change,
                edges=lineage,
                changed_fields=frozenset({"formula"}),
                occurred_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
            )
            == ()
        )


def test_related_change_propagates_and_unrelated_field_does_not() -> None:
    lineage = [edge(DependencyType.COMPUTATIONAL, frozenset({"formula", "rounding"}))]
    source_event_id = uuid4()
    related = propagate_change(
        source_event_id=source_event_id,
        change_type=UpstreamChangeType.PUBLISH_EFFECTIVE,
        edges=lineage,
        changed_fields=frozenset({"formula"}),
        occurred_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    unrelated = propagate_change(
        source_event_id=source_event_id,
        change_type=UpstreamChangeType.PUBLISH_EFFECTIVE,
        edges=lineage,
        changed_fields=frozenset({"display_name"}),
        occurred_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    repeated = propagate_change(
        source_event_id=source_event_id,
        change_type=UpstreamChangeType.PUBLISH_EFFECTIVE,
        edges=lineage,
        changed_fields=frozenset({"formula"}),
        occurred_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    assert len(related) == 1
    assert related[0].effect == InvalidationEffect.STALE
    assert unrelated == ()
    assert repeated[0].idempotency_fingerprint == related[0].idempotency_fingerprint


def test_authorization_event_only_follows_authorization_edges() -> None:
    lineage = [
        edge(DependencyType.AUTHORIZATION, frozenset({"purpose"})),
        edge(DependencyType.PRESENTATIONAL, frozenset({"purpose"})),
    ]
    events = propagate_change(
        source_event_id=uuid4(),
        change_type=UpstreamChangeType.AUTHORIZATION_WITHDRAWN,
        edges=lineage,
        changed_fields=frozenset({"purpose"}),
        occurred_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    assert len(events) == 1
    assert events[0].effect == InvalidationEffect.INVALIDATED


def test_retention_expiry_immediately_blocks_formal_use_even_under_legal_hold() -> None:
    expires_at = datetime(2026, 8, 13, tzinfo=timezone.utc)
    job = RetentionDispositionJob(
        retention_job_id=uuid4(),
        target=ScopedObjectRef(
            tenant_id=TENANT_A,
            data_domain_id=DOMAIN_A,
            object_type="DerivedDataAssetVersion",
            object_id=uuid4(),
        ),
        retention_expires_at=expires_at,
        action=RetentionAction.DELETE,
        state=RetentionJobState.SCHEDULED,
    )
    transition = evaluate_retention_expiry(
        job,
        trusted_now=datetime(2026, 8, 14, tzinfo=timezone.utc),
        active_legal_hold_count=1,
    )
    assert transition.job.formal_use_blocked_at is not None
    assert transition.job.state == RetentionJobState.WAITING_FOR_HOLD_RELEASE
    assert transition.emit_retention_expired is True
    assert transition.request_physical_disposition is False
