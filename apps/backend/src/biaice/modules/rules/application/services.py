"""Application services for member-2 FR-01 scope, regimes and rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock
from biaice.core.errors import BiaiceError
from biaice.core.http import assert_etag, compute_etag
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.core.versioning import VersionMetadata
from biaice.modules.projects.application.repository import Fr01Repository
from biaice.modules.projects.application.services import (
    LifecycleService,
    require_unit,
)
from biaice.modules.projects.domain.lifecycle import DecisionUnitLifecycleState
from biaice.modules.projects.domain.models import ResourceLifecycle, ResourceValidity, canonical_hash
from biaice.modules.projects.domain.resolution import resolve_inherited_clauses
from biaice.modules.rules.domain.models import (
    ApplicableRegime,
    ComplianceReview,
    ComplianceReviewState,
    CrossLotConstraint,
    EvaluationMethod,
    ProcurementMode,
    RoundKind,
    RuleClause,
    RuleClauseKind,
    RuleResolution,
    RuleScopeLevel,
    RuleSet,
    ScopeAssessment,
    ScopeSupport,
    SourceLocator,
)

_COMPLIANCE_EDGES: dict[ComplianceReviewState, frozenset[ComplianceReviewState]] = {
    ComplianceReviewState.OPEN: frozenset(
        {
            ComplianceReviewState.BLOCKING,
            ComplianceReviewState.ACCEPTED_FOR_SIMULATION,
            ComplianceReviewState.RESOLVED,
            ComplianceReviewState.CLOSED,
        }
    ),
    ComplianceReviewState.BLOCKING: frozenset(
        {
            ComplianceReviewState.ACCEPTED_FOR_SIMULATION,
            ComplianceReviewState.RESOLVED,
        }
    ),
    ComplianceReviewState.ACCEPTED_FOR_SIMULATION: frozenset(
        {
            ComplianceReviewState.BLOCKING,
            ComplianceReviewState.RESOLVED,
            ComplianceReviewState.CLOSED,
        }
    ),
    ComplianceReviewState.RESOLVED: frozenset({ComplianceReviewState.CLOSED}),
    ComplianceReviewState.CLOSED: frozenset(),
}


def _emit_event(
    outbox_port: OutboxPort | None,
    *,
    identity: IdentityContext,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: Mapping[str, Any],
    request_id: str,
    project_id: UUID | None = None,
    decision_unit_id: UUID | None = None,
) -> None:
    if outbox_port is None:
        return
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type=event_type,
        schema_version=1,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        occurred_at=datetime.now(timezone.utc),
        actor_id=identity.subject_id,
        request_id=request_id,
        correlation_id=uuid4(),
        causation_id=None,
        payload=dict(payload),
    )
    outbox_port.append(scope=identity.scope, event=envelope)


def _version(
    *,
    actor_id: UUID,
    now: datetime,
    payload: Mapping[str, Any],
    number: int = 1,
    supersedes: UUID | None = None,
) -> VersionMetadata:
    return VersionMetadata(
        version_id=uuid4(),
        version_number=number,
        created_at=now,
        created_by=actor_id,
        content_hash=canonical_hash(payload),
        supersedes_version_id=supersedes,
    )


def _stale_current_scopes(
    repository: Fr01Repository, identity: IdentityContext, unit_id: UUID
) -> None:
    for item in repository.list_scopes(scope=identity.scope, unit_id=unit_id):
        if item.validity_state is ResourceValidity.CURRENT and item.lifecycle_state is ResourceLifecycle.PUBLISHED:
            repository.upsert_scope(
                item.model_copy(update={"validity_state": ResourceValidity.STALE})
            )


def _stale_current_regimes(
    repository: Fr01Repository, identity: IdentityContext, unit_id: UUID
) -> None:
    for item in repository.list_regimes(scope=identity.scope, unit_id=unit_id):
        if item.validity_state is ResourceValidity.CURRENT and item.lifecycle_state is ResourceLifecycle.PUBLISHED:
            repository.upsert_regime(
                item.model_copy(update={"validity_state": ResourceValidity.STALE})
            )


def _stale_current_rule_sets(
    repository: Fr01Repository, identity: IdentityContext, incoming: RuleSet
) -> list[RuleSet]:
    revoked: list[RuleSet] = []
    for item in repository.list_rule_sets(scope=identity.scope, unit_id=incoming.decision_unit_id):
        if item.rule_set_id == incoming.rule_set_id:
            continue
        if item.validity_state is not ResourceValidity.CURRENT:
            continue
        if item.lifecycle_state is not ResourceLifecycle.PUBLISHED:
            continue
        same_project_level = (
            incoming.scope_level is RuleScopeLevel.PROJECT
            and item.scope_level is RuleScopeLevel.PROJECT
            and item.project_id == incoming.project_id
        )
        same_unit_level = (
            incoming.scope_level is RuleScopeLevel.DECISION_UNIT
            and item.scope_level is RuleScopeLevel.DECISION_UNIT
            and item.decision_unit_id == incoming.decision_unit_id
        )
        if not (same_project_level or same_unit_level):
            continue
        stale = item.model_copy(update={"validity_state": ResourceValidity.STALE})
        repository.upsert_rule_set(stale)
        revoked.append(stale)
    return revoked


class ScopeAssessmentService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        lifecycle: LifecycleService,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port
        self.lifecycle = lifecycle

    def create(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        support: ScopeSupport,
        round_kind: RoundKind,
        cross_lot: bool,
        reason_codes: tuple[str, ...],
        source: SourceLocator | None,
        applicability: str | None,
        request_id: str,
    ) -> ScopeAssessment:
        require_audit(self.audit_writer)
        unit = require_unit(self.repository, identity, unit_id)
        now = self.clock.now()
        item = ScopeAssessment(
            scope_assessment_id=uuid4(),
            decision_unit_id=unit.decision_unit_id,
            project_id=unit.project_id,
            tenant_id=unit.tenant_id,
            data_domain_id=unit.data_domain_id,
            support=support,
            round_kind=round_kind,
            cross_lot=cross_lot,
            reason_codes=reason_codes,
            source=source,
            applicability=applicability,
            lifecycle_state=ResourceLifecycle.DRAFT,
            validity_state=ResourceValidity.CURRENT,
            version=_version(
                actor_id=identity.subject_id,
                now=now,
                payload={"support": support.value, "round_kind": round_kind.value},
            ),
        )
        self.repository.upsert_scope(item)
        self.audit_writer.write(
            identity=identity,
            action="rules.scope.create",
            object_type="ScopeAssessment",
            object_id=item.scope_assessment_id,
            request_id=request_id,
            reason_code="SCOPE_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext, unit_id: UUID) -> tuple[ScopeAssessment, ...]:
        require_unit(self.repository, identity, unit_id)
        return self.repository.list_scopes(scope=identity.scope, unit_id=unit_id)

    def get(self, *, identity: IdentityContext, scope_assessment_id: UUID) -> ScopeAssessment:
        item = self.repository.get_scope(scope=identity.scope, scope_assessment_id=scope_assessment_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        return item

    def update_draft(
        self,
        *,
        identity: IdentityContext,
        scope_assessment_id: UUID,
        if_match: str,
        support: ScopeSupport | None,
        round_kind: RoundKind | None,
        cross_lot: bool | None,
        reason_codes: tuple[str, ...] | None,
        applicability: str | None,
        request_id: str,
    ) -> ScopeAssessment:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, scope_assessment_id=scope_assessment_id)
        if current.lifecycle_state is not ResourceLifecycle.DRAFT:
            raise BiaiceError("REQUEST_VALIDATION_FAILED")
        assert_etag(compute_etag(current.version.content_hash), if_match)
        now = self.clock.now()
        updated = current.model_copy(
            update={
                "support": support or current.support,
                "round_kind": round_kind or current.round_kind,
                "cross_lot": current.cross_lot if cross_lot is None else cross_lot,
                "reason_codes": current.reason_codes if reason_codes is None else reason_codes,
                "applicability": current.applicability if applicability is None else applicability,
                "version": _version(
                    actor_id=identity.subject_id,
                    now=now,
                    payload={"support": (support or current.support).value},
                    number=current.version.version_number + 1,
                    supersedes=current.version.version_id,
                ),
            }
        )
        self.repository.upsert_scope(updated)
        self.audit_writer.write(
            identity=identity,
            action="rules.scope.update_draft",
            object_type="ScopeAssessment",
            object_id=updated.scope_assessment_id,
            request_id=request_id,
            reason_code="SCOPE_DRAFT_UPDATED",
            outcome=updated.lifecycle_state.value,
            object_version_id=updated.version.version_id,
        )
        return updated

    def publish(
        self,
        *,
        identity: IdentityContext,
        scope_assessment_id: UUID,
        request_id: str,
    ) -> ScopeAssessment:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, scope_assessment_id=scope_assessment_id)
        if current.lifecycle_state is ResourceLifecycle.PUBLISHED:
            raise BiaiceError("REQUEST_VALIDATION_FAILED")
        if identity.subject_id == current.version.created_by:
            raise BiaiceError(
                "MAKER_CHECKER_REQUIRED",
                detail="The scope drafter cannot also publish the assessment.",
            )
        now = self.clock.now()
        _stale_current_scopes(self.repository, identity, current.decision_unit_id)
        published = current.model_copy(
            update={
                "lifecycle_state": ResourceLifecycle.PUBLISHED,
                "validity_state": ResourceValidity.CURRENT,
                "effective_from": now,
                "confirmed_by": identity.subject_id,
                "confirmed_at": now,
            }
        )
        self.repository.upsert_scope(published)
        unit = require_unit(self.repository, identity, current.decision_unit_id)
        self.repository.upsert_unit(
            unit.model_copy(update={"current_scope_assessment_id": published.scope_assessment_id})
        )
        command = None
        if published.round_kind is RoundKind.MULTI_ROUND or published.support is ScopeSupport.MULTI_ROUND_UNSUPPORTED:
            command = DecisionUnitLifecycleState.MULTI_ROUND_UNSUPPORTED.value
        elif published.cross_lot or published.support is ScopeSupport.PORTFOLIO_REVIEW_REQUIRED:
            command = DecisionUnitLifecycleState.PORTFOLIO_REVIEW_REQUIRED.value
        elif published.support is ScopeSupport.SUPPORTED:
            command = DecisionUnitLifecycleState.RULES_PENDING_CONFIRMATION.value
        if command:
            self.lifecycle.submit_after_intake(
                identity=identity,
                unit_id=unit.decision_unit_id,
                command=command,
                reason="scope assessment published",
                basis=str(published.scope_assessment_id),
                earliest_affected_stage=command,
                request_id=request_id,
            )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="rules.scope_assessment_published.v1",
            aggregate_type="ScopeAssessment",
            aggregate_id=published.scope_assessment_id,
            payload={
                "scope_assessment_id": str(published.scope_assessment_id),
                "decision_unit_id": str(published.decision_unit_id),
                "support": published.support.value,
                "validity": published.validity_state.value,
                "effective_from": now.isoformat(),
            },
            request_id=request_id,
            project_id=published.project_id,
            decision_unit_id=published.decision_unit_id,
        )
        self.audit_writer.write(
            identity=identity,
            action="rules.scope.publish",
            object_type="ScopeAssessment",
            object_id=published.scope_assessment_id,
            request_id=request_id,
            reason_code="SCOPE_PUBLISHED",
            outcome=published.support.value,
            object_version_id=published.version.version_id,
        )
        return published


class ApplicableRegimeService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        regime_name: str,
        procurement_mode: ProcurementMode,
        evaluation_method: EvaluationMethod,
        round_kind: RoundKind,
        source: SourceLocator | None,
        request_id: str,
    ) -> ApplicableRegime:
        require_audit(self.audit_writer)
        unit = require_unit(self.repository, identity, unit_id)
        now = self.clock.now()
        item = ApplicableRegime(
            applicable_regime_id=uuid4(),
            decision_unit_id=unit.decision_unit_id,
            project_id=unit.project_id,
            tenant_id=unit.tenant_id,
            data_domain_id=unit.data_domain_id,
            regime_name=regime_name,
            procurement_mode=procurement_mode,
            evaluation_method=evaluation_method,
            round_kind=round_kind,
            source=source,
            lifecycle_state=ResourceLifecycle.DRAFT,
            validity_state=ResourceValidity.CURRENT,
            version=_version(
                actor_id=identity.subject_id,
                now=now,
                payload={"regime_name": regime_name, "evaluation_method": evaluation_method.value},
            ),
        )
        self.repository.upsert_regime(item)
        self.audit_writer.write(
            identity=identity,
            action="rules.regime.create",
            object_type="ApplicableRegime",
            object_id=item.applicable_regime_id,
            request_id=request_id,
            reason_code="REGIME_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext, unit_id: UUID) -> tuple[ApplicableRegime, ...]:
        require_unit(self.repository, identity, unit_id)
        return self.repository.list_regimes(scope=identity.scope, unit_id=unit_id)

    def get(self, *, identity: IdentityContext, applicable_regime_id: UUID) -> ApplicableRegime:
        item = self.repository.get_regime(scope=identity.scope, applicable_regime_id=applicable_regime_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def publish(self, *, identity: IdentityContext, applicable_regime_id: UUID, request_id: str) -> ApplicableRegime:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, applicable_regime_id=applicable_regime_id)
        if current.lifecycle_state is ResourceLifecycle.PUBLISHED:
            raise BiaiceError("REQUEST_VALIDATION_FAILED")
        if identity.subject_id == current.version.created_by:
            raise BiaiceError("MAKER_CHECKER_REQUIRED", detail="The regime drafter cannot also publish.")
        now = self.clock.now()
        _stale_current_regimes(self.repository, identity, current.decision_unit_id)
        published = current.model_copy(
            update={
                "lifecycle_state": ResourceLifecycle.PUBLISHED,
                "validity_state": ResourceValidity.CURRENT,
                "effective_from": now,
                "confirmed_by": identity.subject_id,
                "confirmed_at": now,
            }
        )
        self.repository.upsert_regime(published)
        unit = require_unit(self.repository, identity, current.decision_unit_id)
        self.repository.upsert_unit(
            unit.model_copy(update={"current_regime_id": published.applicable_regime_id})
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="rules.regime_published.v1",
            aggregate_type="ApplicableRegime",
            aggregate_id=published.applicable_regime_id,
            payload={
                "applicable_regime_id": str(published.applicable_regime_id),
                "decision_unit_id": str(published.decision_unit_id),
                "evaluation_method": published.evaluation_method.value,
                "effective_from": now.isoformat(),
            },
            request_id=request_id,
            project_id=published.project_id,
            decision_unit_id=published.decision_unit_id,
        )
        self.audit_writer.write(
            identity=identity,
            action="rules.regime.publish",
            object_type="ApplicableRegime",
            object_id=published.applicable_regime_id,
            request_id=request_id,
            reason_code="REGIME_PUBLISHED",
            outcome=published.evaluation_method.value,
            object_version_id=published.version.version_id,
        )
        return published


class RuleSetService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        title: str,
        scope_level: RuleScopeLevel,
        effective_from: datetime | None,
        effective_until: datetime | None,
        request_id: str,
    ) -> RuleSet:
        require_audit(self.audit_writer)
        unit = require_unit(self.repository, identity, unit_id)
        now = self.clock.now()
        item = RuleSet(
            rule_set_id=uuid4(),
            decision_unit_id=unit.decision_unit_id,
            project_id=unit.project_id,
            tenant_id=unit.tenant_id,
            data_domain_id=unit.data_domain_id,
            title=title,
            scope_level=scope_level,
            lifecycle_state=ResourceLifecycle.DRAFT,
            validity_state=ResourceValidity.CURRENT,
            version=_version(actor_id=identity.subject_id, now=now, payload={"title": title}),
            effective_from=effective_from,
            effective_until=effective_until,
        )
        self.repository.upsert_rule_set(item)
        self.audit_writer.write(
            identity=identity,
            action="rules.rule_set.create",
            object_type="RuleSet",
            object_id=item.rule_set_id,
            request_id=request_id,
            reason_code="RULE_SET_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext, unit_id: UUID) -> tuple[RuleSet, ...]:
        require_unit(self.repository, identity, unit_id)
        return self.repository.list_rule_sets(scope=identity.scope, unit_id=unit_id)

    def get(self, *, identity: IdentityContext, rule_set_id: UUID) -> RuleSet:
        item = self.repository.get_rule_set(scope=identity.scope, rule_set_id=rule_set_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def publish(self, *, identity: IdentityContext, rule_set_id: UUID, request_id: str) -> RuleSet:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, rule_set_id=rule_set_id)
        if current.lifecycle_state is ResourceLifecycle.PUBLISHED:
            raise BiaiceError("REQUEST_VALIDATION_FAILED")
        if identity.subject_id == current.version.created_by:
            raise BiaiceError("MAKER_CHECKER_REQUIRED", detail="The rule-set drafter cannot also publish.")
        now = self.clock.now()
        effective = current.effective_from or now
        if effective > now:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Future-dated rule sets do not publish as CURRENT and must not invalidate downstream.",
            )
        revoked = _stale_current_rule_sets(self.repository, identity, current)
        published = current.model_copy(
            update={
                "lifecycle_state": ResourceLifecycle.PUBLISHED,
                "validity_state": ResourceValidity.CURRENT,
                "effective_from": effective,
                "confirmed_by": identity.subject_id,
                "confirmed_at": now,
            }
        )
        self.repository.upsert_rule_set(published)
        unit = require_unit(self.repository, identity, current.decision_unit_id)
        self.repository.upsert_unit(unit.model_copy(update={"current_rule_set_id": published.rule_set_id}))
        for old in revoked:
            _emit_event(
                self.outbox_port,
                identity=identity,
                event_type="rules.rule_set_revoked.v1",
                aggregate_type="RuleSet",
                aggregate_id=old.rule_set_id,
                payload={
                    "rule_set_id": str(old.rule_set_id),
                    "successor_rule_set_id": str(published.rule_set_id),
                    "decision_unit_id": str(old.decision_unit_id),
                },
                request_id=request_id,
                project_id=old.project_id,
                decision_unit_id=old.decision_unit_id,
            )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="rules.rule_set_published.v1",
            aggregate_type="RuleSet",
            aggregate_id=published.rule_set_id,
            payload={
                "rule_set_id": str(published.rule_set_id),
                "decision_unit_id": str(published.decision_unit_id),
                "effective_from": effective.isoformat(),
            },
            request_id=request_id,
            project_id=published.project_id,
            decision_unit_id=published.decision_unit_id,
        )
        self.audit_writer.write(
            identity=identity,
            action="rules.rule_set.publish",
            object_type="RuleSet",
            object_id=published.rule_set_id,
            request_id=request_id,
            reason_code="RULE_SET_PUBLISHED",
            outcome=published.lifecycle_state.value,
            object_version_id=published.version.version_id,
        )
        return published


class RuleClauseService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        rule_set_id: UUID,
        kind: RuleClauseKind,
        coverage_key: str,
        priority: int,
        original_text: str,
        structured_expression: str | None,
        confidence: float,
        source: SourceLocator | None,
        request_id: str,
    ) -> RuleClause:
        require_audit(self.audit_writer)
        rule_set = self.repository.get_rule_set(scope=identity.scope, rule_set_id=rule_set_id)
        if rule_set is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        now = self.clock.now()
        item = RuleClause(
            rule_clause_id=uuid4(),
            rule_set_id=rule_set.rule_set_id,
            decision_unit_id=rule_set.decision_unit_id,
            project_id=rule_set.project_id,
            tenant_id=rule_set.tenant_id,
            data_domain_id=rule_set.data_domain_id,
            kind=kind,
            coverage_key=coverage_key,
            priority=priority,
            original_text=original_text,
            structured_expression=structured_expression,
            confidence=confidence,
            source=source,
            lifecycle_state=ResourceLifecycle.DRAFT,
            validity_state=ResourceValidity.CURRENT,
            version=_version(
                actor_id=identity.subject_id,
                now=now,
                payload={"coverage_key": coverage_key, "kind": kind.value},
            ),
        )
        self.repository.upsert_clause(item)
        self.audit_writer.write(
            identity=identity,
            action="rules.clause.create",
            object_type="RuleClause",
            object_id=item.rule_clause_id,
            request_id=request_id,
            reason_code="RULE_CLAUSE_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext, rule_set_id: UUID) -> tuple[RuleClause, ...]:
        rule_set = self.repository.get_rule_set(scope=identity.scope, rule_set_id=rule_set_id)
        if rule_set is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return self.repository.list_clauses(scope=identity.scope, rule_set_id=rule_set_id)

    def get(self, *, identity: IdentityContext, rule_clause_id: UUID) -> RuleClause:
        item = self.repository.get_clause(scope=identity.scope, rule_clause_id=rule_clause_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def update_draft(
        self,
        *,
        identity: IdentityContext,
        rule_clause_id: UUID,
        if_match: str,
        original_text: str | None,
        structured_expression: str | None,
        priority: int | None,
        confidence: float | None,
        request_id: str,
    ) -> RuleClause:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, rule_clause_id=rule_clause_id)
        if current.lifecycle_state is not ResourceLifecycle.DRAFT:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Published clauses cannot be patched; supersede them.",
            )
        assert_etag(compute_etag(current.version.content_hash), if_match)
        now = self.clock.now()
        updated = current.model_copy(
            update={
                "original_text": original_text or current.original_text,
                "structured_expression": current.structured_expression
                if structured_expression is None
                else structured_expression,
                "priority": current.priority if priority is None else priority,
                "confidence": current.confidence if confidence is None else confidence,
                "version": _version(
                    actor_id=identity.subject_id,
                    now=now,
                    payload={"coverage_key": current.coverage_key},
                    number=current.version.version_number + 1,
                    supersedes=current.version.version_id,
                ),
            }
        )
        self.repository.upsert_clause(updated)
        self.audit_writer.write(
            identity=identity,
            action="rules.clause.update_draft",
            object_type="RuleClause",
            object_id=updated.rule_clause_id,
            request_id=request_id,
            reason_code="RULE_CLAUSE_DRAFT_UPDATED",
            outcome=updated.lifecycle_state.value,
            object_version_id=updated.version.version_id,
        )
        return updated

    def supersede(
        self,
        *,
        identity: IdentityContext,
        rule_clause_id: UUID,
        original_text: str,
        structured_expression: str | None,
        request_id: str,
    ) -> RuleClause:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, rule_clause_id=rule_clause_id)
        if current.lifecycle_state is ResourceLifecycle.DRAFT:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Supersede applies to published clauses; patch drafts instead.",
            )
        now = self.clock.now()
        self.repository.upsert_clause(
            current.model_copy(update={"validity_state": ResourceValidity.STALE})
        )
        successor = current.model_copy(
            update={
                "rule_clause_id": uuid4(),
                "original_text": original_text,
                "structured_expression": structured_expression,
                "supersedes_clause_id": current.rule_clause_id,
                "lifecycle_state": ResourceLifecycle.PUBLISHED,
                "validity_state": ResourceValidity.CURRENT,
                "confirmed_by": identity.subject_id,
                "confirmed_at": now,
                "version": _version(
                    actor_id=identity.subject_id,
                    now=now,
                    payload={"coverage_key": current.coverage_key, "supersedes": str(current.rule_clause_id)},
                    number=current.version.version_number + 1,
                    supersedes=current.version.version_id,
                ),
            }
        )
        self.repository.upsert_clause(successor)
        self.audit_writer.write(
            identity=identity,
            action="rules.clause.supersede",
            object_type="RuleClause",
            object_id=successor.rule_clause_id,
            request_id=request_id,
            reason_code="RULE_CLAUSE_SUPERSEDED",
            outcome=successor.validity_state.value,
            object_version_id=successor.version.version_id,
        )
        return successor

    def resolve_unit(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        formal: bool = True,
    ) -> tuple[RuleResolution, ...]:
        require_unit(self.repository, identity, unit_id)
        return resolve_inherited_clauses(
            clauses=self.repository.list_all_clauses_for_unit(scope=identity.scope, unit_id=unit_id),
            rule_sets=self.repository.list_rule_sets(scope=identity.scope, unit_id=unit_id),
            now=self.clock.now(),
            formal=formal,
        )


class ComplianceReviewService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port

    def create(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        finding: str,
        blocking: bool,
        request_id: str,
    ) -> ComplianceReview:
        require_audit(self.audit_writer)
        unit = require_unit(self.repository, identity, unit_id)
        now = self.clock.now()
        state = ComplianceReviewState.BLOCKING if blocking else ComplianceReviewState.OPEN
        item = ComplianceReview(
            compliance_review_id=uuid4(),
            decision_unit_id=unit.decision_unit_id,
            project_id=unit.project_id,
            tenant_id=unit.tenant_id,
            data_domain_id=unit.data_domain_id,
            state=state,
            finding=finding,
            blocking=blocking,
            version=_version(actor_id=identity.subject_id, now=now, payload={"finding": finding}),
        )
        self.repository.upsert_review(item)
        self.audit_writer.write(
            identity=identity,
            action="rules.compliance.create",
            object_type="ComplianceReview",
            object_id=item.compliance_review_id,
            request_id=request_id,
            reason_code=state.value,
            outcome=state.value,
            object_version_id=item.version.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext, unit_id: UUID) -> tuple[ComplianceReview, ...]:
        require_unit(self.repository, identity, unit_id)
        return self.repository.list_reviews(scope=identity.scope, unit_id=unit_id)

    def get(self, *, identity: IdentityContext, compliance_review_id: UUID) -> ComplianceReview:
        item = self.repository.get_review(scope=identity.scope, compliance_review_id=compliance_review_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def transition(
        self,
        *,
        identity: IdentityContext,
        compliance_review_id: UUID,
        target: ComplianceReviewState,
        request_id: str,
    ) -> ComplianceReview:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, compliance_review_id=compliance_review_id)
        if target not in _COMPLIANCE_EDGES[current.state]:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail=f"{current.state.value} cannot move to {target.value}.",
            )
        if current.state is ComplianceReviewState.BLOCKING and target is ComplianceReviewState.CLOSED:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="BLOCKING reviews can only explore; they cannot close into a formal path.",
            )
        updated = current.model_copy(
            update={"state": target, "blocking": target is ComplianceReviewState.BLOCKING}
        )
        self.repository.upsert_review(updated)
        self.audit_writer.write(
            identity=identity,
            action="rules.compliance.transition",
            object_type="ComplianceReview",
            object_id=updated.compliance_review_id,
            request_id=request_id,
            reason_code=target.value,
            outcome=target.value,
            object_version_id=updated.version.version_id,
        )
        return updated


class CrossLotConstraintService:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        lifecycle: LifecycleService,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port
        self.lifecycle = lifecycle

    def create(
        self,
        *,
        identity: IdentityContext,
        unit_id: UUID,
        related_unit_ids: tuple[UUID, ...],
        description: str,
        request_id: str,
    ) -> CrossLotConstraint:
        require_audit(self.audit_writer)
        unit = require_unit(self.repository, identity, unit_id)
        now = self.clock.now()
        item = CrossLotConstraint(
            cross_lot_constraint_id=uuid4(),
            decision_unit_id=unit.decision_unit_id,
            project_id=unit.project_id,
            tenant_id=unit.tenant_id,
            data_domain_id=unit.data_domain_id,
            related_unit_ids=related_unit_ids,
            description=description,
            confirmed=False,
            version=_version(actor_id=identity.subject_id, now=now, payload={"description": description}),
        )
        self.repository.upsert_constraint(item)
        self.audit_writer.write(
            identity=identity,
            action="rules.cross_lot.create",
            object_type="CrossLotConstraint",
            object_id=item.cross_lot_constraint_id,
            request_id=request_id,
            reason_code="CROSS_LOT_DRAFT",
            outcome="UNCONFIRMED",
            object_version_id=item.version.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext, unit_id: UUID) -> tuple[CrossLotConstraint, ...]:
        require_unit(self.repository, identity, unit_id)
        return self.repository.list_constraints(scope=identity.scope, unit_id=unit_id)

    def get(self, *, identity: IdentityContext, cross_lot_constraint_id: UUID) -> CrossLotConstraint:
        item = self.repository.get_constraint(
            scope=identity.scope, cross_lot_constraint_id=cross_lot_constraint_id
        )
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def confirm(
        self, *, identity: IdentityContext, cross_lot_constraint_id: UUID, request_id: str
    ) -> CrossLotConstraint:
        require_audit(self.audit_writer)
        current = self.get(identity=identity, cross_lot_constraint_id=cross_lot_constraint_id)
        now = self.clock.now()
        confirmed = current.model_copy(
            update={"confirmed": True, "confirmed_by": identity.subject_id, "confirmed_at": now}
        )
        self.repository.upsert_constraint(confirmed)
        self.lifecycle.submit_after_intake(
            identity=identity,
            unit_id=current.decision_unit_id,
            command=DecisionUnitLifecycleState.PORTFOLIO_REVIEW_REQUIRED.value,
            reason="cross-lot constraint confirmed",
            basis=str(confirmed.cross_lot_constraint_id),
            earliest_affected_stage="PORTFOLIO_REVIEW_REQUIRED",
            request_id=request_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="rules.cross_lot_constraint_confirmed.v1",
            aggregate_type="CrossLotConstraint",
            aggregate_id=confirmed.cross_lot_constraint_id,
            payload={
                "cross_lot_constraint_id": str(confirmed.cross_lot_constraint_id),
                "decision_unit_id": str(confirmed.decision_unit_id),
                "related_unit_ids": [str(item) for item in confirmed.related_unit_ids],
            },
            request_id=request_id,
            project_id=confirmed.project_id,
            decision_unit_id=confirmed.decision_unit_id,
        )
        self.audit_writer.write(
            identity=identity,
            action="rules.cross_lot.confirm",
            object_type="CrossLotConstraint",
            object_id=confirmed.cross_lot_constraint_id,
            request_id=request_id,
            reason_code="CROSS_LOT_CONFIRMED",
            outcome="PORTFOLIO_REVIEW_REQUIRED",
            object_version_id=confirmed.version.version_id,
        )
        return confirmed


class RulesServices:
    def __init__(
        self,
        *,
        repository: Fr01Repository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        lifecycle: LifecycleService,
    ) -> None:
        self.repository = repository
        self.scope = ScopeAssessmentService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
            lifecycle=lifecycle,
        )
        self.regimes = ApplicableRegimeService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.rule_sets = RuleSetService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.clauses = RuleClauseService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.reviews = ComplianceReviewService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
        )
        self.cross_lot = CrossLotConstraintService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
            lifecycle=lifecycle,
        )
