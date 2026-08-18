"""Immutable FR-09b risk acceptance models (member 7 first slice).

RiskAcceptanceVersion is append-only: creation produces ACTIVE/CURRENT and
revocation produces REVOKED/INVALIDATED with immutable revocation metadata.
Expiry is derived at read time from the validity period, never overwritten.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RiskAcceptanceState(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class RiskAcceptanceValidity(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class RiskAcceptance(FrozenModel):
    risk_acceptance_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    state: RiskAcceptanceState
    validity: RiskAcceptanceValidity
    risk: str = Field(min_length=1, max_length=200)
    metric: str = Field(min_length=1, max_length=200)
    acceptance_scope: str = Field(min_length=1, max_length=400)
    rationale: str = Field(min_length=1, max_length=2000)
    independent_approver_id: UUID
    valid_from: datetime
    valid_until: datetime
    created_at: datetime
    created_by: UUID
    accepted_at: datetime
    accepted_by: UUID
    revoked_at: datetime | None = None
    revoked_by: UUID | None = None
    revocation_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def maker_and_checker_must_be_independent(self) -> "RiskAcceptance":
        if self.created_by == self.independent_approver_id:
            raise ValueError("maker and independent approver must be different")
        if self.accepted_by != self.independent_approver_id:
            raise ValueError("accepted_by must be the independent approver")
        return self

    @model_validator(mode="after")
    def validity_period_must_be_ordered(self) -> "RiskAcceptance":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        return self

    @model_validator(mode="after")
    def state_and_validity_must_agree(self) -> "RiskAcceptance":
        if self.state is RiskAcceptanceState.ACTIVE:
            if self.validity is not RiskAcceptanceValidity.CURRENT:
                raise ValueError("ACTIVE risk acceptance must be CURRENT")
        elif self.state is RiskAcceptanceState.REVOKED:
            if self.validity is not RiskAcceptanceValidity.INVALIDATED:
                raise ValueError("REVOKED risk acceptance must be INVALIDATED")
            if self.revoked_at is None or self.revoked_by is None or not self.revocation_reason:
                raise ValueError("REVOKED risk acceptance requires revocation metadata")
        elif self.validity is not RiskAcceptanceValidity.EXPIRED:
            raise ValueError("EXPIRED risk acceptance must be EXPIRED")
        return self


def effective_risk_acceptance(item: RiskAcceptance, *, now: datetime) -> RiskAcceptance:
    """Return the read-time projection without mutating persisted history."""
    if item.state is RiskAcceptanceState.ACTIVE and now >= item.valid_until:
        return item.model_copy(
            update={
                "state": RiskAcceptanceState.EXPIRED,
                "validity": RiskAcceptanceValidity.EXPIRED,
            }
        )
    return item
