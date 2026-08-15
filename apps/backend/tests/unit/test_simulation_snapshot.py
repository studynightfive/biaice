"""Unit tests for the SHADOW_PILOT_LOCKED snapshot helper."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    SHADOW_PILOT_LOCKED_WATERMARK,
    SnapshotState,
)
from biaice.modules.simulation.domain.snapshot import (
    SnapshotRequest,
    assert_shadow_watermark,
    compute_payload_hash,
    create_snapshot,
)


NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def _request(payload=None) -> SnapshotRequest:
    return SnapshotRequest(
        snapshot_id=uuid4(),
        version_id=uuid4(),
        tenant_id=uuid4(),
        data_domain_id=uuid4(),
        project_id=None,
        decision_unit_id=uuid4(),
        payload=payload if payload is not None else {"k": "v"},
        created_at=NOW,
        created_by=uuid4(),
        lock=True,
    )


def test_create_snapshot_carries_shadow_pilot_locked_watermark() -> None:
    snapshot = create_snapshot(_request())
    assert snapshot.watermark == SHADOW_PILOT_LOCKED_WATERMARK
    assert snapshot.state == SnapshotState.LOCKED
    assert snapshot.payload_hash == compute_payload_hash(snapshot.payload)


def test_create_snapshot_rejects_empty_payload() -> None:
    with pytest.raises(BiaiceError) as error:
        create_snapshot(_request(payload={}))
    assert error.value.code == "SNAPSHOT_PAYLOAD_HASH_MISMATCH"


def test_assert_shadow_watermark_rejects_tampering() -> None:
    snapshot = create_snapshot(_request())
    tampered = snapshot.model_copy(update={"watermark": "TAMPERED"})
    with pytest.raises(BiaiceError) as error:
        assert_shadow_watermark(tampered)
    assert error.value.code == "SNAPSHOT_PAYLOAD_HASH_MISMATCH"


def test_create_snapshot_when_lock_false_stays_draft() -> None:
    snapshot = create_snapshot(_request())
    draft = create_snapshot(SnapshotRequest(
        snapshot_id=uuid4(),
        version_id=uuid4(),
        tenant_id=uuid4(),
        data_domain_id=uuid4(),
        project_id=None,
        decision_unit_id=uuid4(),
        payload={"k": "v"},
        created_at=NOW,
        created_by=uuid4(),
        lock=False,
    ))
    assert draft.state == SnapshotState.DRAFT
    assert draft.locked_at is None
    # the locked snapshot from _request must still validate watermark
    assert_shadow_watermark(snapshot)
