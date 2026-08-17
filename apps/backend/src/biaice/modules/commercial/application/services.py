"""FR-04 services. Commercial refusal is never rewritten as tender invalidity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.modules.evidence.application.errors import m4_error
from biaice.core.money import Money
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.modules.commercial.application.ports import (
    MarketReadinessPort,
    UnavailableMarketReadinessPort,
)
from biaice.modules.commercial.application.repository import (
    CommercialRepository,
    InMemoryCommercialRepository,
)
from biaice.modules.commercial.domain.models import (
    CommercialPolicy,
    CostBaseline,
    ReadinessDecision,
    ReadinessItem,
    StrategyReadinessAssessment,
    TaxMode,
)
from biaice.modules.evidence.application.ports import (
    EvidenceReadinessPort,
    EvidenceReadinessView,
)
from biaice.modules.evidence.domain.models import (
    LifecycleState,
    PrecheckDecision,
    ReviewState,
    ValidityState,
    formal_input_allowed,
)


def _project_id(identity: IdentityContext) -> UUID | None:
    return next(iter(identity.scope.project_ids), None)


def _assert_unit(identity: IdentityContext, decision_unit_id: UUID) -> None:
    identity.scope.assert_allows(
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        decision_unit_id=decision_unit_id,
    )


def _emit_event(
    outbox_port: OutboxPort | None,
    *,
    identity: IdentityContext,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: Mapping[str, Any],
    request_id: str,
) -> None:
    if outbox_port is None:
        return
    outbox_port.append(
        scope=identity.scope,
        event=EventEnvelope(
            event_id=uuid4(),
            event_type=event_type,
            schema_version=1,
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=next(iter(identity.scope.decision_unit_ids), None),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            actor_id=identity.subject_id,
            request_id=request_id,
            correlation_id=uuid4(),
            causation_id=None,
            payload=dict(payload),
        ),
    )


class _EmptyEvidenceReadiness:
    def current_view(self, *, scope, decision_unit_id: UUID) -> EvidenceReadinessView:
        del scope, decision_unit_id
        return EvidenceReadinessView(
            precheck_decision=None,
            precheck_validity=None,
            response_profile_current=False,
            subject_qualification=None,
            unmapped_mandatory_count=0,
            open_blocking_condition_count=0,
        )


class CommercialService:
    def __init__(
        self,
        *,
        repository: CommercialRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        evidence_readiness_port: EvidenceReadinessPort,
        market_readiness_port: MarketReadinessPort,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port
        self.evidence_readiness_port = evidence_readiness_port
        self.market_readiness_port = market_readiness_port

    def _audit(self, **kwargs: Any) -> None:
        require_audit(self.audit_writer)
        self.audit_writer.write(**kwargs)

    def create_cost_baseline(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        currency: str,
        tax_mode: TaxMode,
        input_vat: Money,
        cycle: str,
        delivery_cost: Money,
        post_award_cost: Money,
        bid_preparation_cost: Money,
        cashflow_in: Money,
        cashflow_out: Money,
        request_id: str,
    ) -> CostBaseline:
        _assert_unit(identity, decision_unit_id)
        item = CostBaseline(
            cost_baseline_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            currency=currency,
            tax_mode=tax_mode,
            input_vat=input_vat,
            cycle=cycle,
            delivery_cost=delivery_cost,
            post_award_cost=post_award_cost,
            bid_preparation_cost=bid_preparation_cost,
            cashflow_in=cashflow_in,
            cashflow_out=cashflow_out,
            lifecycle_state=LifecycleState.DRAFT,
            review_state=ReviewState.PENDING,
            validity_state=ValidityState.CURRENT,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
            exploration_only=True,
        )
        self.repository.upsert_cost(item)
        self._audit(
            identity=identity,
            action="commercial.cost.create",
            object_type="CostBaseline",
            object_id=item.cost_baseline_id,
            request_id=request_id,
            reason_code="COST_DRAFT_CREATED",
            outcome="EXPLORATION_ONLY",
            object_version_id=item.version_id,
        )
        return item

    def list_cost_baselines(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[CostBaseline, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_costs(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_cost_baseline(self, *, identity: IdentityContext, cost_baseline_id: UUID) -> CostBaseline:
        item = self.repository.get_cost(scope=identity.scope, cost_baseline_id=cost_baseline_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def approve_cost_baseline(
        self, *, identity: IdentityContext, cost_baseline_id: UUID, request_id: str
    ) -> CostBaseline:
        item = self.get_cost_baseline(identity=identity, cost_baseline_id=cost_baseline_id)
        if identity.subject_id == item.created_by:
            raise BiaiceError("MAKER_CHECKER_REQUIRED")
        if item.approved_by is not None:
            raise m4_error("COST_ALREADY_APPROVED")
        approved = item.model_copy(
            update={
                "review_state": ReviewState.APPROVED,
                "approved_at": self.clock.now(),
                "approved_by": identity.subject_id,
            }
        )
        self.repository.upsert_cost(approved)
        self._audit(
            identity=identity,
            action="commercial.cost.approve",
            object_type="CostBaseline",
            object_id=approved.cost_baseline_id,
            request_id=request_id,
            reason_code="COST_APPROVED",
            outcome=approved.review_state.value,
            object_version_id=approved.version_id,
        )
        return approved

    def publish_cost_baseline(
        self, *, identity: IdentityContext, cost_baseline_id: UUID, request_id: str
    ) -> CostBaseline:
        item = self.get_cost_baseline(identity=identity, cost_baseline_id=cost_baseline_id)
        if item.review_state is not ReviewState.APPROVED or item.approved_by is None:
            raise m4_error("COST_NOT_APPROVED")
        if item.lifecycle_state is not LifecycleState.DRAFT:
            raise m4_error("PUBLISHED_VERSION_IMMUTABLE")
        now = self.clock.now()
        published = item.model_copy(
            update={
                "lifecycle_state": LifecycleState.PUBLISHED,
                "validity_state": ValidityState.CURRENT,
                "effective_from": now,
                "published_at": now,
                "published_by": identity.subject_id,
                "exploration_only": False,
            }
        )
        self.repository.upsert_cost(published)
        self._audit(
            identity=identity,
            action="commercial.cost.publish",
            object_type="CostBaseline",
            object_id=published.cost_baseline_id,
            request_id=request_id,
            reason_code="COST_PUBLISHED",
            outcome=published.lifecycle_state.value,
            object_version_id=published.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.cost_baseline_published.v1",
            aggregate_type="CostBaseline",
            aggregate_id=published.cost_baseline_id,
            payload={
                "cost_baseline_id": str(published.cost_baseline_id),
                "decision_unit_id": str(published.decision_unit_id),
                "currency": published.currency,
            },
            request_id=request_id,
        )
        return published

    def create_policy(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        profit_floor: str,
        cashflow_constraint: str,
        capacity_constraint: str,
        risk_threshold: str,
        coverage_ratio: str,
        min_award_quality: str,
        objective_weights: dict[str, str],
        merge_tolerance: str,
        exception_authority: str,
        request_id: str,
    ) -> CommercialPolicy:
        _assert_unit(identity, decision_unit_id)
        item = CommercialPolicy(
            policy_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            profit_floor=profit_floor,
            cashflow_constraint=cashflow_constraint,
            capacity_constraint=capacity_constraint,
            risk_threshold=risk_threshold,
            coverage_ratio=coverage_ratio,
            min_award_quality=min_award_quality,
            objective_weights=objective_weights,
            merge_tolerance=merge_tolerance,
            exception_authority=exception_authority,
            lifecycle_state=LifecycleState.DRAFT,
            review_state=ReviewState.PENDING,
            validity_state=ValidityState.CURRENT,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
        )
        self.repository.upsert_policy(item)
        self._audit(
            identity=identity,
            action="commercial.policy.create",
            object_type="CommercialPolicy",
            object_id=item.policy_id,
            request_id=request_id,
            reason_code="POLICY_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version_id,
        )
        return item

    def list_policies(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[CommercialPolicy, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_policies(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_policy(self, *, identity: IdentityContext, policy_id: UUID) -> CommercialPolicy:
        item = self.repository.get_policy(scope=identity.scope, policy_id=policy_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def publish_policy(
        self, *, identity: IdentityContext, policy_id: UUID, request_id: str
    ) -> CommercialPolicy:
        item = self.get_policy(identity=identity, policy_id=policy_id)
        if item.lifecycle_state is not LifecycleState.DRAFT:
            raise m4_error("PUBLISHED_VERSION_IMMUTABLE")
        now = self.clock.now()
        published = item.model_copy(
            update={
                "lifecycle_state": LifecycleState.PUBLISHED,
                "review_state": ReviewState.APPROVED,
                "effective_from": now,
                "published_at": now,
                "published_by": identity.subject_id,
            }
        )
        self.repository.upsert_policy(published)
        self._audit(
            identity=identity,
            action="commercial.policy.publish",
            object_type="CommercialPolicy",
            object_id=published.policy_id,
            request_id=request_id,
            reason_code="POLICY_PUBLISHED",
            outcome=published.lifecycle_state.value,
            object_version_id=published.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.commercial_policy_published.v1",
            aggregate_type="CommercialPolicy",
            aggregate_id=published.policy_id,
            payload={
                "policy_id": str(published.policy_id),
                "decision_unit_id": str(published.decision_unit_id),
            },
            request_id=request_id,
        )
        return published

    def create_readiness(
        self, *, identity: IdentityContext, decision_unit_id: UUID, request_id: str
    ) -> StrategyReadinessAssessment:
        _assert_unit(identity, decision_unit_id)
        now = self.clock.now()
        evidence_view = self.evidence_readiness_port.current_view(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )
        market_view = self.market_readiness_port.current_view(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )
        costs = self.repository.list_costs(scope=identity.scope, decision_unit_id=decision_unit_id)
        policies = self.repository.list_policies(scope=identity.scope, decision_unit_id=decision_unit_id)
        current_cost = next(
            (item for item in reversed(costs) if formal_input_allowed(item, now=now).allowed),
            None,
        )
        draft_cost = next((item for item in reversed(costs) if item.exploration_only), None)
        current_policy = next(
            (item for item in reversed(policies) if formal_input_allowed(item, now=now).allowed),
            None,
        )

        def item(code: str, decision: ReadinessDecision, reason: str, commercial: bool = False) -> ReadinessItem:
            return ReadinessItem(
                code=code,
                decision=decision,
                reason_code=reason,
                commercial_not_procurement=commercial,
            )

        if evidence_view.precheck_decision is None:
            rules_item = item("rules", ReadinessDecision.UNKNOWN, "PRECHECK_MISSING")
            precheck_item = item("precheck", ReadinessDecision.UNKNOWN, "PRECHECK_MISSING")
        elif evidence_view.precheck_decision is PrecheckDecision.PASS:
            rules_item = item("rules", ReadinessDecision.READY, "PRECHECK_PASS")
            precheck_item = item("precheck", ReadinessDecision.READY, "PRECHECK_PASS")
        elif evidence_view.precheck_decision is PrecheckDecision.CONDITIONAL:
            rules_item = item("rules", ReadinessDecision.CONDITIONAL, "PRECHECK_CONDITIONAL")
            precheck_item = item("precheck", ReadinessDecision.CONDITIONAL, "PRECHECK_CONDITIONAL")
        elif evidence_view.precheck_decision is PrecheckDecision.BLOCKED:
            rules_item = item("rules", ReadinessDecision.NOT_READY, "PRECHECK_BLOCKED")
            precheck_item = item("precheck", ReadinessDecision.NOT_READY, "PRECHECK_BLOCKED")
        else:
            rules_item = item("rules", ReadinessDecision.UNKNOWN, "PRECHECK_UNKNOWN")
            precheck_item = item("precheck", ReadinessDecision.UNKNOWN, "PRECHECK_UNKNOWN")

        response_item = item(
            "response",
            ReadinessDecision.READY if evidence_view.response_profile_current else ReadinessDecision.NOT_READY,
            "RESPONSE_CURRENT" if evidence_view.response_profile_current else "RESPONSE_MISSING",
        )
        if current_cost is not None:
            cost_item = item("cost", ReadinessDecision.READY, "COST_PUBLISHED", commercial=True)
        elif draft_cost is not None:
            cost_item = item("cost", ReadinessDecision.NOT_READY, "COST_EXPLORATION_ONLY", commercial=True)
        else:
            cost_item = item("cost", ReadinessDecision.UNKNOWN, "COST_MISSING", commercial=True)
        policy_item = item(
            "policy",
            ReadinessDecision.READY if current_policy is not None else ReadinessDecision.NOT_READY,
            "POLICY_PUBLISHED" if current_policy is not None else "POLICY_MISSING",
            commercial=True,
        )
        if market_view is None:
            market_item = item("market", ReadinessDecision.UNKNOWN, "MARKET_PORT_UNAVAILABLE")
            data_use_item = item("data_use", ReadinessDecision.UNKNOWN, "MARKET_PORT_UNAVAILABLE")
            model_item = item("model", ReadinessDecision.UNKNOWN, "MARKET_PORT_UNAVAILABLE")
        else:
            market_item = item(
                "market",
                ReadinessDecision.READY if market_view.prior_current else ReadinessDecision.NOT_READY,
                "PRESSURE_ONLY" if market_view.pressure_only else "MARKET_PRIOR_CURRENT",
            )
            data_use_item = item(
                "data_use",
                ReadinessDecision.READY if market_view.data_use_authorized else ReadinessDecision.NOT_READY,
                "DATA_USE_OK" if market_view.data_use_authorized else "DATA_USE_BLOCKED",
            )
            model_item = item(
                "model",
                ReadinessDecision.READY if market_view.model_protocol_current else ReadinessDecision.NOT_READY,
                "MODEL_PROTOCOL_CURRENT" if market_view.model_protocol_current else "MODEL_PROTOCOL_MISSING",
            )
        scenario_item = item("scenario_protocol", ReadinessDecision.UNKNOWN, "SCENARIO_PORT_MEMBER_6")

        items = (
            rules_item,
            precheck_item,
            response_item,
            cost_item,
            policy_item,
            market_item,
            data_use_item,
            model_item,
            scenario_item,
        )
        decisions = {entry.decision for entry in items}
        if ReadinessDecision.UNKNOWN in decisions and ReadinessDecision.NOT_READY not in decisions:
            overall = ReadinessDecision.UNKNOWN
        elif ReadinessDecision.NOT_READY in decisions:
            overall = ReadinessDecision.NOT_READY
        elif ReadinessDecision.CONDITIONAL in decisions:
            overall = ReadinessDecision.CONDITIONAL
        else:
            overall = ReadinessDecision.READY
        assessment = StrategyReadinessAssessment(
            readiness_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            decision=overall,
            validity_state=ValidityState.CURRENT,
            items=items,
            created_at=now,
            created_by=identity.subject_id,
            exploration_watermark=overall is not ReadinessDecision.READY,
        )
        self.repository.upsert_readiness(assessment)
        self._audit(
            identity=identity,
            action="commercial.readiness.create",
            object_type="StrategyReadinessAssessment",
            object_id=assessment.readiness_id,
            request_id=request_id,
            reason_code="READINESS_ASSESSED",
            outcome=assessment.decision.value,
            object_version_id=assessment.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.readiness_assessed.v1",
            aggregate_type="StrategyReadinessAssessment",
            aggregate_id=assessment.readiness_id,
            payload={
                "readiness_id": str(assessment.readiness_id),
                "decision": assessment.decision.value,
                "exploration_watermark": assessment.exploration_watermark,
            },
            request_id=request_id,
        )
        return assessment

    def list_readiness(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[StrategyReadinessAssessment, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_readiness(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_readiness(
        self, *, identity: IdentityContext, readiness_id: UUID
    ) -> StrategyReadinessAssessment:
        item = self.repository.get_readiness(scope=identity.scope, readiness_id=readiness_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item


class CommercialServices:
    def __init__(
        self,
        *,
        repository: CommercialRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        evidence_readiness_port: EvidenceReadinessPort,
        market_readiness_port: MarketReadinessPort,
    ) -> None:
        self.repository = repository
        self.commercial = CommercialService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
            evidence_readiness_port=evidence_readiness_port,
            market_readiness_port=market_readiness_port,
        )


def configure_commercial(
    app,
    *,
    repository: CommercialRepository | None = None,
    evidence_readiness_port: EvidenceReadinessPort | None = None,
    market_readiness_port: MarketReadinessPort | None = None,
) -> CommercialServices:
    repository = repository or InMemoryCommercialRepository()
    services = CommercialServices(
        repository=repository,
        clock=SystemClock(),
        audit_writer=app.state.audit_writer,
        outbox_port=getattr(app.state, "outbox_port", None),
        evidence_readiness_port=evidence_readiness_port
        or getattr(app.state, "evidence_readiness_port", None)
        or _EmptyEvidenceReadiness(),
        market_readiness_port=market_readiness_port
        or getattr(app.state, "market_readiness_port", None)
        or UnavailableMarketReadinessPort(),
    )
    app.state.commercial_repository = repository
    app.state.commercial_services = services
    return services
