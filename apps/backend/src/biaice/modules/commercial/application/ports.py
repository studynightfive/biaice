"""FR-04 ports. Market/model facts come from member 5; never invent priors."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from biaice.core.auth import TenantScope


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MarketReadinessView(FrozenModel):
    prior_current: bool
    pressure_only: bool
    model_protocol_current: bool
    data_use_authorized: bool


class MarketReadinessPort(Protocol):
    def current_view(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> MarketReadinessView | None: ...


class UnavailableMarketReadinessPort:
    def current_view(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> None:
        del scope, decision_unit_id
        return None
