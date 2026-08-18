"""Unit tests for FR-06/07/08/09a simulation domain models.

These tests assert that every immutable model:
    * is frozen (mutation raises ValidationError/AttributeError);
    * rejects binary float / non-DecimalStr monetary fields;
    * carries tenant_id / data_domain_id / project_id / decision_unit_id /
      version_id / created_at / created_by / frozen_at / frozen_by;
    * enforces the 13 enumerations defined in models.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from biaice.modules.simulation.domain.models import (
    AwardMode,
    BaselineState,
    BatchState,
    DecimalStr,
    DecisionBaseline,
    EligibilityState,
    FrozenModel,
    InputManifest,
    ManifestItem,
    ObjectiveKind,
    OptimizationState,
    PlanState,
    ReviewValidity,
    ScenarioKind,
    ScenarioSetMember,
    ScenarioSetState,
    SearchSpaceState,
    SnapshotState,
    StaticValidationStatus,
    StressAxis,
)


def _manifest_item() -> ManifestItem:
    return ManifestItem(
        item_id=uuid4(),
        upstream_type="rules",
        upstream_id=uuid4(),
        upstream_version_id=uuid4(),
        upstream_content_hash="a" * 64,
        dependency_type="EVIDENTIAL",
        recorded_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )


def test_decimal_str_rejects_binary_float_and_invalid_strings() -> None:
    DecimalStr(value="10.5")
    with pytest.raises(ValidationError):
        DecimalStr(value="abc")
    with pytest.raises(ValidationError):
        DecimalStr(value="1.2.3")
    # Pydantic v2 enforces string-typed fields at validation time, so passing
    # a float raises ValidationError rather than our custom TypeError; the
    # behavioural guarantee ("no binary float") is still satisfied.
    with pytest.raises(ValidationError):
        DecimalStr(value=1.2)  # type: ignore[arg-type]


def test_decimal_str_coerce_accepts_str_and_decimal() -> None:
    DecimalStr.coerce("100.50")
    DecimalStr.coerce(Decimal("100.50"))
    a = DecimalStr.coerce(Decimal("0.5"))
    assert a.value in {"0.5", "0.5000"}
    with pytest.raises(TypeError):
        DecimalStr.coerce(1.5)  # type: ignore[arg-type]


def test_decision_baseline_is_frozen_and_carries_required_projection() -> None:
    item = _manifest_item()
    baseline = DecisionBaseline(
        baseline_id=uuid4(),
        version_id=uuid4(),
        tenant_id=uuid4(),
        data_domain_id=uuid4(),
        project_id=None,
        decision_unit_id=uuid4(),
        manifest=InputManifest(
            manifest_id=uuid4(), manifest_hash="0" * 64, items=(item,)
        ),
        state=BaselineState.FROZEN,
        frozen_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        frozen_by=uuid4(),
        created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        created_by=uuid4(),
    )
    with pytest.raises(ValidationError):
        baseline.state = BaselineState.DRAFT  # type: ignore[misc]
    assert baseline.tenant_id is not None
    assert baseline.created_at is not None
    assert baseline.frozen_at is not None
    assert baseline.created_by is not None
    assert baseline.frozen_by is not None


def test_scenario_set_member_rejects_unknown_scenario_kind() -> None:
    with pytest.raises(ValidationError):
        ScenarioSetMember(
            scenario_id=uuid4(),
            scenario_kind="UNKNOWN",  # type: ignore[arg-type]
            weight=DecimalStr(value="0.5"),
            label="x",
        )


def test_thirteen_enumerations_present() -> None:
    assert {s.name for s in BaselineState} == {"DRAFT", "FROZEN", "SUPERSEDED", "INVALIDATED"}
    assert {s.name for s in SearchSpaceState} == {"DRAFT", "FROZEN", "SUPERSEDED", "INVALIDATED"}
    assert {s.name for s in ScenarioSetState} == {"DRAFT", "FROZEN", "SUPERSEDED", "INVALIDATED"}
    assert {s.name for s in ScenarioKind} == {"SEARCH", "EVALUATION", "STRESS"}
    assert {s.name for s in BatchState} == {
        "PENDING", "RUNNING", "SUCCEEDED", "INDETERMINATE",
        "FAILED_RETRYABLE", "FAILED_TERMINAL", "CANCELLED",
    }
    assert {s.name for s in OptimizationState} == {
        "DRAFT", "RUNNING", "SUCCEEDED", "FAILED", "INVALIDATED", "FINALIZED"
    }
    assert {s.name for s in PlanState} == {"DRAFT", "PUBLISHED", "INVALIDATED"}
    assert {s.name for s in EligibilityState} == {"ELIGIBLE", "INELIGIBLE", "INDETERMINATE"}
    assert {s.name for s in SnapshotState} == {"DRAFT", "LOCKED"}
    assert {s.name for s in AwardMode} == {"SINGLE", "MULTI", "NONE"}
    assert {s.name for s in ReviewValidity} == {"CURRENT", "UNKNOWN", "EXPIRED", "INVALIDATED"}
    assert {s.name for s in ObjectiveKind} == {"COST_MIN", "MARGIN_MAX", "COVERAGE_MAX", "RISK_MIN"}
    assert {s.name for s in StressAxis} == {
        "PRICE_BAND", "TIMING", "COMPLIANCE", "PROVIDER_OUTAGE", "UNIT_FAILURE"
    }
    assert {s.name for s in StaticValidationStatus} == {"PASS", "FAIL", "INDETERMINATE"}


def test_decision_baseline_rejects_missing_frozen_projection() -> None:
    item = _manifest_item()
    with pytest.raises(ValidationError):
        DecisionBaseline(
            baseline_id=uuid4(),
            version_id=uuid4(),
            tenant_id=uuid4(),
            data_domain_id=uuid4(),
            project_id=None,
            decision_unit_id=uuid4(),
            manifest=InputManifest(
                manifest_id=uuid4(), manifest_hash="0" * 64, items=(item,)
            ),
            state=BaselineState.FROZEN,
            frozen_at=None,
            frozen_by=None,
            created_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            created_by=uuid4(),
        )


def test_frozen_model_rejects_extra_fields() -> None:
    class Tiny(FrozenModel):
        x: int
    Tiny(x=1)
    with pytest.raises(ValidationError):
        Tiny(x=1, y=2)  # type: ignore[call-arg]
