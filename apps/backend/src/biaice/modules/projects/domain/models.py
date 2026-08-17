"""Immutable FR-01 project and decision-unit models (member 2)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from biaice.core.money import Money
from biaice.core.versioning import VersionMetadata
from biaice.modules.projects.domain.lifecycle import DecisionUnitLifecycleState


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResourceLifecycle(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ResourceValidity(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


def canonical_hash(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ProcurementProject(FrozenModel):
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    name: str = Field(min_length=1, max_length=200)
    purchaser_name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(min_length=1, max_length=64)
    budget: Money | None = None
    price_ceiling: Money | None = None
    deadline_at: datetime | None = None
    cross_unit_group_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)
    lifecycle_state: ResourceLifecycle
    validity_state: ResourceValidity
    version: VersionMetadata
    archived_at: datetime | None = None
    archived_by: UUID | None = None

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_iana_like(cls, value: str) -> str:
        if "/" not in value and value not in {"UTC", "GMT"}:
            raise ValueError("timezone must be an IANA name such as Asia/Shanghai")
        return value


class DecisionUnit(FrozenModel):
    decision_unit_id: UUID
    project_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    name: str = Field(min_length=1, max_length=200)
    lot_code: str | None = Field(default=None, max_length=80)
    timezone: str = Field(min_length=1, max_length=64)
    budget: Money | None = None
    price_ceiling: Money | None = None
    deadline_at: datetime | None = None
    cross_unit_group_id: UUID | None = None
    lifecycle_state: DecisionUnitLifecycleState
    resource_lifecycle: ResourceLifecycle
    validity_state: ResourceValidity
    version: VersionMetadata
    current_scope_assessment_id: UUID | None = None
    current_regime_id: UUID | None = None
    current_rule_set_id: UUID | None = None
    gap_summary: str | None = Field(default=None, max_length=2000)

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_iana_like(cls, value: str) -> str:
        if "/" not in value and value not in {"UTC", "GMT"}:
            raise ValueError("timezone must be an IANA name such as Asia/Shanghai")
        return value


class DocumentIntakeRef(FrozenModel):
    """Locator-only projection of a member-3 public document event."""

    event_id: UUID
    event_type: str
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    document_id: UUID | None = None
    parse_job_id: UUID | None = None
    usable_for_formal_rules: bool
    validity_state: ResourceValidity
    occurred_at: datetime
    request_id: str = Field(min_length=1, max_length=128)


class DecisionUnitLifecycleEvent(FrozenModel):
    event_id: UUID
    decision_unit_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID
    sequence: int = Field(ge=1)
    command: str = Field(min_length=1, max_length=80)
    from_state: DecisionUnitLifecycleState
    to_state: DecisionUnitLifecycleState
    reopened: bool = False
    reason: str = Field(min_length=1, max_length=2000)
    basis: str | None = Field(default=None, max_length=2000)
    earliest_affected_stage: str | None = Field(default=None, max_length=80)
    actor_id: UUID
    occurred_at: datetime
    request_id: str


class DocumentIntakeRef(FrozenModel):
    """Locator-only projection of member-3 public events. No file bytes."""

    event_id: UUID
    event_type: str = Field(min_length=1, max_length=120)
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    document_id: UUID | None = None
    parse_job_id: UUID | None = None
    usable_for_formal_rules: bool
    validity_state: ResourceValidity
    occurred_at: datetime
    request_id: str = Field(min_length=1, max_length=128)
