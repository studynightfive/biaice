"""Input-manifest hashing for decision baselines.

The manifest hash pins upstream rule, response, cost, policy, market and model
references together with their SHA-256 content hashes. Any drift between
the frozen manifest and the live upstream forces a new baseline version
(BASELINE_INCOMPLETE / STALE_BASELINE); the simulation services refuse to
create or freeze a batch that depends on a hash the world cannot prove.

All functions are pure and frozen — the application layer is responsible for
serializing manifest entries in a deterministic order.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence
from uuid import UUID

from biaice.core.errors import BiaiceError
from biaice.modules.simulation.domain.models import (
    DecisionBaseline,
    InputManifest,
    ManifestItem,
    new_uuid,
)


def canonical_item(item: ManifestItem) -> Mapping[str, Any]:
    """Return the JSON-canonical projection of a manifest item."""
    return {
        "item_id": str(item.item_id),
        "upstream_type": item.upstream_type,
        "upstream_id": str(item.upstream_id),
        "upstream_version_id": str(item.upstream_version_id),
        "upstream_content_hash": item.upstream_content_hash,
        "dependency_type": item.dependency_type,
        "recorded_at": item.recorded_at.isoformat(),
    }


def compute_input_manifest_hash(items: Sequence[ManifestItem]) -> str:
    """Return the deterministic SHA-256 manifest hash.

    Items must already be sorted by the caller; sorting here would mask the
    contract that producers commit to a stable order. Returning a hex digest
    guarantees the value matches `^[a-f0-9]{64}$` for Pydantic validation.
    """
    payload = [canonical_item(item) for item in items]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_manifest(items: Sequence[ManifestItem]) -> InputManifest:
    """Wrap items in an InputManifest with a canonical hash."""
    if not items:
        raise BiaiceError(
            "BASELINE_INCOMPLETE",
            detail=(
                "决策基线 input manifest 不能为空 / Decision baseline input manifest must "
                "contain at least one upstream reference."
            ),
        )
    return InputManifest(
        manifest_id=new_uuid(),
        manifest_hash=compute_input_manifest_hash(items),
        items=tuple(items),
    )


def verify_manifest(manifest: InputManifest, items: Sequence[ManifestItem]) -> bool:
    """Return True iff the committed hash still matches the recomputed hash."""
    expected = compute_input_manifest_hash(items)
    return manifest.manifest_hash == expected


def assert_manifest_complete(baseline: DecisionBaseline) -> None:
    """Raise BASELINE_INCOMPLETE when a baseline references no manifest items."""
    if not baseline.manifest.items:
        raise BiaiceError(
            "BASELINE_INCOMPLETE",
            detail=(
                "决策基线缺少上游 input manifest 条目 / Decision baseline references no "
                "upstream input manifest items."
            ),
        )
    verify = verify_manifest(baseline.manifest, baseline.manifest.items)
    if not verify:
        raise BiaiceError(
            "BASELINE_INCOMPLETE",
            detail=(
                "决策基线 manifest hash 与 items 不一致 / Decision baseline manifest hash "
                "does not match the recorded items."
            ),
        )


def assert_manifest_matches_versions(
    baseline: DecisionBaseline,
    live_versions: Mapping[UUID, str],
) -> None:
    """Raise STALE_BASELINE when any recorded upstream version moved.

    `live_versions` maps the upstream_version_id to the current content hash
    as seen by the relevant module (rules/responses/cost/policy/market/model).
    """
    drift: list[str] = []
    for item in baseline.manifest.items:
        live_hash = live_versions.get(item.upstream_version_id)
        if live_hash is None or live_hash != item.upstream_content_hash:
            drift.append(f"{item.upstream_type}:{item.upstream_version_id}")
    if drift:
        raise BiaiceError(
            "STALE_BASELINE",
            detail=(
                "决策基线已陈旧，上游版本已变更 / Decision baseline is stale; upstream "
                f"versions drifted: {', '.join(drift)}. Freeze a new baseline version."
            ),
        )
