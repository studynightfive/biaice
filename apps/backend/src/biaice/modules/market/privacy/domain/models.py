"""Synthetic-safe FR-12 transport and state-record models.

The command envelope is intentionally narrower than the eventual legal DTOs:
it accepts only explicit synthetic metadata and is unsuitable for real personal
data until the M0 and REAL_DATA_MODE gates are signed and passed.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, TypeAlias
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MarketResourceState(StrEnum):
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"
    CLOSED = "CLOSED"
    COMPLETED = "COMPLETED"
    CONTAINED = "CONTAINED"
    CURRENT = "CURRENT"
    DRAFT = "DRAFT"
    EXPIRED = "EXPIRED"
    FROZEN = "FROZEN"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_REQUIRED = "NOT_REQUIRED"
    OPEN = "OPEN"
    PUBLISHED = "PUBLISHED"
    READY_TO_COMPLETE = "READY_TO_COMPLETE"
    RECEIVED = "RECEIVED"
    RECORDED = "RECORDED"
    REJECTED = "REJECTED"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    REVOKED = "REVOKED"
    TRIAGED = "TRIAGED"
    WAITING_FOR_INFORMATION = "WAITING_FOR_INFORMATION"


# OpenAPI represents an optional query value as JSON null. Form-style query
# transports serialize that value as the literal string "null"; the API treats
# it as an omitted filter so generated and real clients share one contract.
MarketResourceStateFilter: TypeAlias = MarketResourceState | Literal["null"] | None


class MarketResourceCommand(FrozenModel):
    """Frozen synthetic metadata envelope; real personal data is forbidden."""

    subject_scope: str | None = Field(default=None, min_length=1, max_length=400)
    justification_ref: str | None = Field(default=None, min_length=1, max_length=500)
    legal_basis_ref: str | None = Field(default=None, min_length=1, max_length=500)
    notice_ref: str | None = Field(default=None, min_length=1, max_length=500)
    policy_ref: str | None = Field(default=None, min_length=1, max_length=500)
    source_ref: str | None = Field(default=None, min_length=1, max_length=500)
    provider_ref: str | None = Field(default=None, min_length=1, max_length=500)
    evidence_refs: tuple[str, ...] | None = Field(default=None, max_length=100)
    purpose: str | None = Field(default=None, min_length=1, max_length=200)
    region: str | None = Field(default=None, min_length=1, max_length=120)
    retention_days: int | None = Field(default=None, ge=0, le=36500)
    delete_plan: str | None = Field(default=None, min_length=1, max_length=1000)
    risk_level: str | None = Field(default=None, min_length=1, max_length=120)
    reviewer: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, min_length=1, max_length=2000)


class MarketActionCommand(FrozenModel):
    reason_code: str | None = Field(default=None, min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=1000)
    target_state: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    effective_at: datetime | None = None
    correlation_id: UUID | None = None


class MarketResourceRecord(FrozenModel):
    resource_id: UUID
    resource_type: str = Field(pattern=r"^[a-z][a-z0-9_]{1,79}$")
    tenant_id: UUID
    data_domain_id: UUID
    state: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    state_version: int = Field(ge=1)
    payload: dict[str, Any]
    status_reason: str | None = Field(default=None, max_length=120)
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID


class MarketResourcePage(FrozenModel):
    items: tuple[MarketResourceRecord, ...] = ()
    next_cursor: str | None = None
    has_more: bool = False
