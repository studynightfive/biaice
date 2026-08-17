"""Immutable FR-04 cost, policy and strategy-readiness models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from biaice.core.money import Money
from biaice.modules.evidence.domain.models import (
    LifecycleState,
    RetentionState,
    ReviewState,
    ValidityState,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TaxMode(StrEnum):
    INCLUSIVE = "INCLUSIVE"
    EXCLUSIVE = "EXCLUSIVE"


class ReadinessDecision(StrEnum):
    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    NOT_READY = "NOT_READY"
    UNKNOWN = "UNKNOWN"


class CostBaseline(FrozenModel):
    cost_baseline_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    tax_mode: TaxMode
    input_vat: Money
    cycle: str = Field(min_length=1, max_length=40)
    delivery_cost: Money
    post_award_cost: Money
    bid_preparation_cost: Money
    cashflow_in: Money
    cashflow_out: Money
    lifecycle_state: LifecycleState
    review_state: ReviewState
    validity_state: ValidityState
    retention_state: RetentionState = RetentionState.RETAIN
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    superseded_by_id: UUID | None = None
    created_at: datetime
    created_by: UUID
    approved_at: datetime | None = None
    approved_by: UUID | None = None
    published_at: datetime | None = None
    published_by: UUID | None = None
    exploration_only: bool

    @model_validator(mode="after")
    def currencies_align(self) -> "CostBaseline":
        for field in (
            self.input_vat,
            self.delivery_cost,
            self.post_award_cost,
            self.bid_preparation_cost,
            self.cashflow_in,
            self.cashflow_out,
        ):
            if field.currency != self.currency:
                raise ValueError("all money fields must use the baseline currency")
        return self

    @model_validator(mode="after")
    def maker_checker(self) -> "CostBaseline":
        if self.approved_by is not None and self.approved_by == self.created_by:
            raise ValueError("cost author cannot approve their own baseline")
        return self


class CommercialPolicy(FrozenModel):
    policy_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    profit_floor: str = Field(min_length=1, max_length=40)
    cashflow_constraint: str = Field(min_length=1, max_length=200)
    capacity_constraint: str = Field(min_length=1, max_length=200)
    risk_threshold: str = Field(min_length=1, max_length=200)
    coverage_ratio: str = Field(min_length=1, max_length=40)
    min_award_quality: str = Field(min_length=1, max_length=80)
    objective_weights: dict[str, str] = Field(default_factory=dict)
    merge_tolerance: str = Field(min_length=1, max_length=40)
    exception_authority: str = Field(min_length=1, max_length=200)
    lifecycle_state: LifecycleState
    review_state: ReviewState
    validity_state: ValidityState
    retention_state: RetentionState = RetentionState.RETAIN
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    superseded_by_id: UUID | None = None
    created_at: datetime
    created_by: UUID
    published_at: datetime | None = None
    published_by: UUID | None = None


class ReadinessItem(FrozenModel):
    code: str
    decision: ReadinessDecision
    reason_code: str
    commercial_not_procurement: bool = False


class StrategyReadinessAssessment(FrozenModel):
    readiness_id: UUID
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID
    decision: ReadinessDecision
    validity_state: ValidityState
    items: tuple[ReadinessItem, ...]
    created_at: datetime
    created_by: UUID
    exploration_watermark: bool
