"""FR-03 application services. Precheck never reads cost, profit or market data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.http import assert_etag, compute_etag
from biaice.core.outbox import EventEnvelope, OutboxPort
from biaice.modules.evidence.application.errors import m4_error
from biaice.modules.evidence.application.ports import (
    DocumentReadPort,
    EvidenceReadinessView,
    ReleasedDocumentRef,
    RuleAvailabilityPort,
    UnavailableDocumentReadPort,
    UnavailableRuleAvailabilityPort,
)
from biaice.modules.evidence.application.repository import (
    EvidenceRepository,
    InMemoryEvidenceRepository,
)
from biaice.modules.evidence.domain.models import (
    BlockingStage,
    CompanyEvidence,
    CompanyResponseProfile,
    ConditionRequirement,
    ConditionState,
    EvidenceCategory,
    EvidenceMatch,
    LifecycleState,
    MatchState,
    PrecheckAssessment,
    PrecheckCheck,
    PrecheckDecision,
    Requirement,
    ReviewState,
    ValidityState,
    condition_is_blocking,
    formal_input_allowed,
)


def _project_id(identity: IdentityContext) -> UUID | None:
    return next(iter(identity.scope.project_ids), None)


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


def _assert_unit(identity: IdentityContext, decision_unit_id: UUID) -> None:
    identity.scope.assert_allows(
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        decision_unit_id=decision_unit_id,
    )


def _as_released_ref(view: object) -> ReleasedDocumentRef | None:
    status = getattr(view, "status", None)
    status_value = getattr(status, "value", status)
    if str(status_value) != "RELEASED":
        return None
    parse_status = getattr(view, "parse_status", None)
    parse_value = getattr(parse_status, "value", parse_status)
    try:
        return ReleasedDocumentRef(
            document_id=getattr(view, "document_id"),
            content_hash=str(getattr(view, "content_hash")),
            status="RELEASED",
            parse_status=None if parse_value is None else str(parse_value),
            fragment_refs=tuple(getattr(view, "fragment_refs", ()) or ()),
        )
    except Exception:
        return None


def _evidence_usable(item: CompanyEvidence, *, now: datetime) -> bool:
    if not formal_input_allowed(item, now=now).allowed:
        return False
    if now < item.valid_from or now >= item.valid_to:
        return False
    return True


class EvidenceService:
    def __init__(
        self,
        *,
        repository: EvidenceRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        document_read_port: DocumentReadPort,
        rule_availability_port: RuleAvailabilityPort,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.outbox_port = outbox_port
        self.document_read_port = document_read_port
        self.rule_availability_port = rule_availability_port

    def _audit(
        self,
        *,
        identity: IdentityContext,
        action: str,
        object_type: str,
        object_id: UUID,
        request_id: str,
        reason_code: str,
        outcome: str,
        object_version_id: UUID | None = None,
    ) -> None:
        require_audit(self.audit_writer)
        self.audit_writer.write(
            identity=identity,
            action=action,
            object_type=object_type,
            object_id=object_id,
            request_id=request_id,
            reason_code=reason_code,
            outcome=outcome,
            object_version_id=object_version_id,
        )

    def _released_document(
        self, *, identity: IdentityContext, document_id: UUID | None
    ) -> ReleasedDocumentRef | None:
        if document_id is None:
            return None
        view = self.document_read_port.get_released_document(
            scope=identity.scope, document_id=document_id
        )
        if view is None:
            return None
        return _as_released_ref(view)

    def create_requirement(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        title: str,
        statement: str,
        mandatory: bool,
        rule_clause_id: UUID | None,
        source_document_id: UUID | None,
        source_page: str | None,
        source_section: str | None,
        request_id: str,
    ) -> Requirement:
        _assert_unit(identity, decision_unit_id)
        if source_document_id is not None and self._released_document(
            identity=identity, document_id=source_document_id
        ) is None:
            raise m4_error(
                "EVIDENCE_DOCUMENT_NOT_RELEASED",
                detail="Requirement citations may only use member-3 released documents.",
            )
        now = self.clock.now()
        requirement_id = uuid4()
        version_id = uuid4()
        item = Requirement(
            requirement_id=requirement_id,
            version_id=version_id,
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            rule_clause_id=rule_clause_id,
            title=title,
            statement=statement,
            mandatory=mandatory,
            source_document_id=source_document_id,
            source_page=source_page,
            source_section=source_section,
            lifecycle_state=LifecycleState.DRAFT,
            review_state=ReviewState.PENDING,
            validity_state=ValidityState.CURRENT,
            etag=compute_etag({"requirement_id": str(requirement_id), "version_id": str(version_id)}),
            created_at=now,
            created_by=identity.subject_id,
        )
        self.repository.upsert_requirement(item)
        self._audit(
            identity=identity,
            action="evidence.requirement.create",
            object_type="Requirement",
            object_id=item.requirement_id,
            request_id=request_id,
            reason_code="REQUIREMENT_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version_id,
        )
        return item

    def list_requirements(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[Requirement, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_requirements(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_requirement(self, *, identity: IdentityContext, requirement_id: UUID) -> Requirement:
        item = self.repository.get_requirement(scope=identity.scope, requirement_id=requirement_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def update_requirement_draft(
        self,
        *,
        identity: IdentityContext,
        requirement_id: UUID,
        title: str,
        statement: str,
        mandatory: bool,
        if_match: str,
        request_id: str,
    ) -> Requirement:
        item = self.get_requirement(identity=identity, requirement_id=requirement_id)
        if item.lifecycle_state is not LifecycleState.DRAFT:
            raise m4_error("PUBLISHED_VERSION_IMMUTABLE")
        assert_etag(item.etag, if_match)
        updated = item.model_copy(
            update={
                "title": title,
                "statement": statement,
                "mandatory": mandatory,
                "etag": compute_etag({"requirement_id": str(item.requirement_id), "title": title, "statement": statement}),
            }
        )
        self.repository.upsert_requirement(updated)
        self._audit(
            identity=identity,
            action="evidence.requirement.update_draft",
            object_type="Requirement",
            object_id=updated.requirement_id,
            request_id=request_id,
            reason_code="REQUIREMENT_DRAFT_UPDATED",
            outcome=updated.lifecycle_state.value,
            object_version_id=updated.version_id,
        )
        return updated

    def publish_requirement(self, *, identity: IdentityContext, requirement_id: UUID, request_id: str) -> Requirement:
        item = self.get_requirement(identity=identity, requirement_id=requirement_id)
        if item.lifecycle_state is not LifecycleState.DRAFT:
            raise m4_error("PUBLISHED_VERSION_IMMUTABLE")
        now = self.clock.now()
        published = item.model_copy(
            update={
                "lifecycle_state": LifecycleState.PUBLISHED,
                "review_state": ReviewState.APPROVED,
                "validity_state": ValidityState.CURRENT,
                "effective_from": now,
                "published_at": now,
                "published_by": identity.subject_id,
                "etag": compute_etag({"requirement_id": str(item.requirement_id), "published": True}),
            }
        )
        self.repository.upsert_requirement(published)
        self._audit(
            identity=identity,
            action="evidence.requirement.publish",
            object_type="Requirement",
            object_id=published.requirement_id,
            request_id=request_id,
            reason_code="REQUIREMENT_PUBLISHED",
            outcome=published.lifecycle_state.value,
            object_version_id=published.version_id,
        )
        return published

    def supersede_requirement(
        self, *, identity: IdentityContext, requirement_id: UUID, request_id: str
    ) -> Requirement:
        item = self.get_requirement(identity=identity, requirement_id=requirement_id)
        if item.lifecycle_state is not LifecycleState.PUBLISHED:
            raise m4_error(
                "REQUIREMENT_NOT_PUBLISHED",
                detail="Only a published requirement can be superseded by a new version.",
            )
        now = self.clock.now()
        successor_id = uuid4()
        successor = item.model_copy(
            update={
                "requirement_id": successor_id,
                "version_id": uuid4(),
                "lifecycle_state": LifecycleState.DRAFT,
                "review_state": ReviewState.PENDING,
                "validity_state": ValidityState.CURRENT,
                "effective_from": None,
                "published_at": None,
                "published_by": None,
                "created_at": now,
                "created_by": identity.subject_id,
                "etag": compute_etag({"requirement_id": str(successor_id), "supersedes": str(item.requirement_id)}),
            }
        )
        stale = item.model_copy(
            update={
                "validity_state": ValidityState.STALE,
                "superseded_by_id": successor.requirement_id,
            }
        )
        self.repository.upsert_requirement(stale)
        self.repository.upsert_requirement(successor)
        self._audit(
            identity=identity,
            action="evidence.requirement.supersede",
            object_type="Requirement",
            object_id=successor.requirement_id,
            request_id=request_id,
            reason_code="REQUIREMENT_SUPERSEDED",
            outcome=successor.lifecycle_state.value,
            object_version_id=successor.version_id,
        )
        return successor

    def create_evidence(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        category: EvidenceCategory,
        subject: str,
        summary: str,
        source: str,
        source_document_id: UUID | None,
        fragment_ref: str | None,
        valid_from: datetime,
        valid_to: datetime,
        request_id: str,
    ) -> CompanyEvidence:
        _assert_unit(identity, decision_unit_id)
        released = self._released_document(identity=identity, document_id=source_document_id)
        if source_document_id is not None and released is None:
            raise m4_error("EVIDENCE_DOCUMENT_NOT_RELEASED")
        item = CompanyEvidence(
            evidence_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            category=category,
            subject=subject,
            summary=summary,
            source=source,
            source_document_id=source_document_id,
            fragment_ref=fragment_ref,
            content_hash=None if released is None else released.content_hash,
            valid_from=valid_from,
            valid_to=valid_to,
            lifecycle_state=LifecycleState.DRAFT,
            review_state=ReviewState.PENDING,
            validity_state=ValidityState.CURRENT,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
        )
        self.repository.upsert_evidence(item)
        self._audit(
            identity=identity,
            action="evidence.evidence.create",
            object_type="CompanyEvidence",
            object_id=item.evidence_id,
            request_id=request_id,
            reason_code="EVIDENCE_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version_id,
        )
        return item

    def list_evidence(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[CompanyEvidence, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_evidence(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_evidence(self, *, identity: IdentityContext, evidence_id: UUID) -> CompanyEvidence:
        item = self.repository.get_evidence(scope=identity.scope, evidence_id=evidence_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def review_evidence(
        self, *, identity: IdentityContext, evidence_id: UUID, request_id: str
    ) -> CompanyEvidence:
        item = self.get_evidence(identity=identity, evidence_id=evidence_id)
        if identity.subject_id == item.created_by:
            raise BiaiceError("MAKER_CHECKER_REQUIRED")
        reviewed = item.model_copy(
            update={
                "review_state": ReviewState.APPROVED,
                "reviewed_at": self.clock.now(),
                "reviewed_by": identity.subject_id,
            }
        )
        self.repository.upsert_evidence(reviewed)
        self._audit(
            identity=identity,
            action="evidence.evidence.review",
            object_type="CompanyEvidence",
            object_id=reviewed.evidence_id,
            request_id=request_id,
            reason_code="EVIDENCE_REVIEWED",
            outcome=reviewed.review_state.value,
            object_version_id=reviewed.version_id,
        )
        return reviewed

    def publish_evidence(
        self, *, identity: IdentityContext, evidence_id: UUID, request_id: str
    ) -> CompanyEvidence:
        item = self.get_evidence(identity=identity, evidence_id=evidence_id)
        if item.lifecycle_state is not LifecycleState.DRAFT:
            raise m4_error("PUBLISHED_VERSION_IMMUTABLE")
        if item.review_state is not ReviewState.APPROVED:
            raise m4_error(
                "EVIDENCE_REVIEW_REQUIRED",
                detail="Evidence must be independently reviewed before publish.",
            )
        now = self.clock.now()
        published = item.model_copy(
            update={
                "lifecycle_state": LifecycleState.PUBLISHED,
                "validity_state": ValidityState.CURRENT,
                "effective_from": now,
                "published_at": now,
                "published_by": identity.subject_id,
            }
        )
        self.repository.upsert_evidence(published)
        self._audit(
            identity=identity,
            action="evidence.evidence.publish",
            object_type="CompanyEvidence",
            object_id=published.evidence_id,
            request_id=request_id,
            reason_code="EVIDENCE_PUBLISHED",
            outcome=published.lifecycle_state.value,
            object_version_id=published.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.evidence_published.v1",
            aggregate_type="CompanyEvidence",
            aggregate_id=published.evidence_id,
            payload={
                "evidence_id": str(published.evidence_id),
                "decision_unit_id": str(published.decision_unit_id),
                "category": published.category.value,
            },
            request_id=request_id,
        )
        return published

    def revoke_evidence(
        self, *, identity: IdentityContext, evidence_id: UUID, reason: str, request_id: str
    ) -> CompanyEvidence:
        item = self.get_evidence(identity=identity, evidence_id=evidence_id)
        now = self.clock.now()
        revoked = item.model_copy(
            update={
                "lifecycle_state": LifecycleState.ARCHIVED,
                "validity_state": ValidityState.INVALIDATED,
                "revoked_at": now,
                "revoked_by": identity.subject_id,
                "revocation_reason": reason,
            }
        )
        self.repository.upsert_evidence(revoked)
        for match in self.repository.list_matches(
            scope=identity.scope, decision_unit_id=item.decision_unit_id
        ):
            if match.evidence_id == evidence_id and match.validity_state is ValidityState.CURRENT:
                self.repository.upsert_match(
                    match.model_copy(
                        update={"state": MatchState.UNKNOWN, "validity_state": ValidityState.STALE}
                    )
                )
        self._audit(
            identity=identity,
            action="evidence.evidence.revoke",
            object_type="CompanyEvidence",
            object_id=revoked.evidence_id,
            request_id=request_id,
            reason_code="EVIDENCE_REVOKED",
            outcome=revoked.lifecycle_state.value,
            object_version_id=revoked.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.evidence_revoked.v1",
            aggregate_type="CompanyEvidence",
            aggregate_id=revoked.evidence_id,
            payload={
                "evidence_id": str(revoked.evidence_id),
                "decision_unit_id": str(revoked.decision_unit_id),
            },
            request_id=request_id,
        )
        return revoked

    def create_match(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        requirement_id: UUID,
        evidence_id: UUID | None,
        requested_state: MatchState,
        rationale: str,
        request_id: str,
    ) -> EvidenceMatch:
        _assert_unit(identity, decision_unit_id)
        requirement = self.get_requirement(identity=identity, requirement_id=requirement_id)
        if requirement.decision_unit_id != decision_unit_id:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        now = self.clock.now()
        evidence = None
        if evidence_id is not None:
            evidence = self.get_evidence(identity=identity, evidence_id=evidence_id)
        resolved_state = requested_state
        if requested_state is MatchState.SATISFIED:
            if evidence is None or not _evidence_usable(evidence, now=now):
                raise m4_error("EVIDENCE_SATISFIED_WITHOUT_PROOF")
        if evidence is None or not _evidence_usable(evidence, now=now):
            resolved_state = MatchState.UNKNOWN
        item = EvidenceMatch(
            match_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            requirement_id=requirement_id,
            evidence_id=evidence_id,
            state=resolved_state,
            rationale=rationale,
            original_etag=requirement.etag,
            created_at=now,
            created_by=identity.subject_id,
        )
        self.repository.upsert_match(item)
        self._audit(
            identity=identity,
            action="evidence.match.create",
            object_type="EvidenceMatch",
            object_id=item.match_id,
            request_id=request_id,
            reason_code="EVIDENCE_MATCH_CREATED",
            outcome=item.state.value,
            object_version_id=item.version_id,
        )
        return item

    def list_matches(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[EvidenceMatch, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_matches(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_match(self, *, identity: IdentityContext, match_id: UUID) -> EvidenceMatch:
        item = self.repository.get_match(scope=identity.scope, match_id=match_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def review_match(
        self,
        *,
        identity: IdentityContext,
        match_id: UUID,
        state: MatchState,
        rationale: str,
        request_id: str,
    ) -> EvidenceMatch:
        item = self.get_match(identity=identity, match_id=match_id)
        if identity.subject_id == item.created_by:
            raise BiaiceError("MAKER_CHECKER_REQUIRED")
        evidence = None
        if item.evidence_id is not None:
            evidence = self.repository.get_evidence(scope=identity.scope, evidence_id=item.evidence_id)
        now = self.clock.now()
        if state is MatchState.SATISFIED and (
            evidence is None or not _evidence_usable(evidence, now=now)
        ):
            raise m4_error("EVIDENCE_SATISFIED_WITHOUT_PROOF")
        reviewed = item.model_copy(
            update={
                "state": state,
                "rationale": rationale,
                "reviewed_at": now,
                "reviewed_by": identity.subject_id,
                "validity_state": ValidityState.CURRENT,
            }
        )
        self.repository.upsert_match(reviewed)
        self._audit(
            identity=identity,
            action="evidence.match.review",
            object_type="EvidenceMatch",
            object_id=reviewed.match_id,
            request_id=request_id,
            reason_code="EVIDENCE_MATCH_REVIEWED",
            outcome=reviewed.state.value,
            object_version_id=reviewed.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.evidence_match_reviewed.v1",
            aggregate_type="EvidenceMatch",
            aggregate_id=reviewed.match_id,
            payload={
                "match_id": str(reviewed.match_id),
                "state": reviewed.state.value,
            },
            request_id=request_id,
        )
        return reviewed

    def create_profile(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        qualification_preparation: str,
        technical_response: str,
        service_response: str,
        objective_non_price_inputs: dict[str, str],
        subjective_variable_intervals: dict[str, str],
        evidence_ids: tuple[UUID, ...],
        valid_from: datetime,
        valid_to: datetime,
        request_id: str,
    ) -> CompanyResponseProfile:
        _assert_unit(identity, decision_unit_id)
        now = self.clock.now()
        for evidence_id in evidence_ids:
            evidence = self.get_evidence(identity=identity, evidence_id=evidence_id)
            if not _evidence_usable(evidence, now=now):
                raise m4_error(
                    "RESPONSE_PROFILE_EVIDENCE_NOT_CURRENT",
                    detail="Response profiles may only cite current published evidence.",
                )
        item = CompanyResponseProfile(
            profile_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            qualification_preparation=qualification_preparation,
            technical_response=technical_response,
            service_response=service_response,
            objective_non_price_inputs=objective_non_price_inputs,
            subjective_variable_intervals=subjective_variable_intervals,
            evidence_ids=evidence_ids,
            valid_from=valid_from,
            valid_to=valid_to,
            lifecycle_state=LifecycleState.DRAFT,
            review_state=ReviewState.NOT_REQUIRED,
            validity_state=ValidityState.CURRENT,
            created_at=now,
            created_by=identity.subject_id,
        )
        self.repository.upsert_profile(item)
        self._audit(
            identity=identity,
            action="evidence.profile.create",
            object_type="CompanyResponseProfile",
            object_id=item.profile_id,
            request_id=request_id,
            reason_code="RESPONSE_PROFILE_DRAFT_CREATED",
            outcome=item.lifecycle_state.value,
            object_version_id=item.version_id,
        )
        return item

    def list_profiles(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[CompanyResponseProfile, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_profiles(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_profile(self, *, identity: IdentityContext, profile_id: UUID) -> CompanyResponseProfile:
        item = self.repository.get_profile(scope=identity.scope, profile_id=profile_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def publish_profile(
        self, *, identity: IdentityContext, profile_id: UUID, request_id: str
    ) -> CompanyResponseProfile:
        item = self.get_profile(identity=identity, profile_id=profile_id)
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
        self.repository.upsert_profile(published)
        self._audit(
            identity=identity,
            action="evidence.profile.publish",
            object_type="CompanyResponseProfile",
            object_id=published.profile_id,
            request_id=request_id,
            reason_code="RESPONSE_PROFILE_PUBLISHED",
            outcome=published.lifecycle_state.value,
            object_version_id=published.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.response_profile_published.v1",
            aggregate_type="CompanyResponseProfile",
            aggregate_id=published.profile_id,
            payload={
                "profile_id": str(published.profile_id),
                "decision_unit_id": str(published.decision_unit_id),
            },
            request_id=request_id,
        )
        return published

    def create_condition(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        title: str,
        statement: str,
        owner_id: UUID,
        independent_reviewer_id: UUID,
        evidence_id: UUID | None,
        due_at: datetime,
        blocking_stage: BlockingStage,
        request_id: str,
    ) -> ConditionRequirement:
        _assert_unit(identity, decision_unit_id)
        if owner_id == independent_reviewer_id:
            raise BiaiceError("MAKER_CHECKER_REQUIRED")
        if evidence_id is not None:
            self.get_evidence(identity=identity, evidence_id=evidence_id)
        item = ConditionRequirement(
            condition_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            title=title,
            statement=statement,
            state=ConditionState.OPEN,
            owner_id=owner_id,
            independent_reviewer_id=independent_reviewer_id,
            evidence_id=evidence_id,
            due_at=due_at,
            blocking_stage=blocking_stage,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
        )
        self.repository.upsert_condition(item)
        self._audit(
            identity=identity,
            action="evidence.condition.create",
            object_type="ConditionRequirement",
            object_id=item.condition_id,
            request_id=request_id,
            reason_code="CONDITION_OPENED",
            outcome=item.state.value,
            object_version_id=item.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.condition_changed.v1",
            aggregate_type="ConditionRequirement",
            aggregate_id=item.condition_id,
            payload={"condition_id": str(item.condition_id), "state": item.state.value},
            request_id=request_id,
        )
        return item

    def list_conditions(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[ConditionRequirement, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_conditions(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_condition(self, *, identity: IdentityContext, condition_id: UUID) -> ConditionRequirement:
        item = self.repository.get_condition(scope=identity.scope, condition_id=condition_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        now = self.clock.now()
        if item.state is ConditionState.OPEN and now >= item.due_at:
            return item.model_copy(update={"state": ConditionState.EXPIRED})
        return item

    def _transition_condition(
        self,
        *,
        identity: IdentityContext,
        condition_id: UUID,
        new_state: ConditionState,
        reason: str,
        request_id: str,
        action: str,
    ) -> ConditionRequirement:
        item = self.repository.get_condition(scope=identity.scope, condition_id=condition_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        current = self.get_condition(identity=identity, condition_id=condition_id)
        if current.state is not ConditionState.OPEN:
            raise m4_error("CONDITION_NOT_OPEN")
        closed = item.model_copy(
            update={
                "state": new_state,
                "closed_at": self.clock.now(),
                "closed_by": identity.subject_id,
                "close_reason": reason,
            }
        )
        self.repository.upsert_condition(closed)
        self._audit(
            identity=identity,
            action=action,
            object_type="ConditionRequirement",
            object_id=closed.condition_id,
            request_id=request_id,
            reason_code=f"CONDITION_{new_state.value}",
            outcome=closed.state.value,
            object_version_id=closed.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.condition_changed.v1",
            aggregate_type="ConditionRequirement",
            aggregate_id=closed.condition_id,
            payload={"condition_id": str(closed.condition_id), "state": closed.state.value},
            request_id=request_id,
        )
        return closed

    def satisfy_condition(self, *, identity: IdentityContext, condition_id: UUID, reason: str, request_id: str) -> ConditionRequirement:
        return self._transition_condition(
            identity=identity,
            condition_id=condition_id,
            new_state=ConditionState.SATISFIED,
            reason=reason,
            request_id=request_id,
            action="evidence.condition.satisfy",
        )

    def waive_condition(self, *, identity: IdentityContext, condition_id: UUID, reason: str, request_id: str) -> ConditionRequirement:
        return self._transition_condition(
            identity=identity,
            condition_id=condition_id,
            new_state=ConditionState.WAIVED,
            reason=reason,
            request_id=request_id,
            action="evidence.condition.waive",
        )

    def fail_condition(self, *, identity: IdentityContext, condition_id: UUID, reason: str, request_id: str) -> ConditionRequirement:
        return self._transition_condition(
            identity=identity,
            condition_id=condition_id,
            new_state=ConditionState.FAILED,
            reason=reason,
            request_id=request_id,
            action="evidence.condition.fail",
        )

    def expire_condition(self, *, identity: IdentityContext, condition_id: UUID, reason: str, request_id: str) -> ConditionRequirement:
        return self._transition_condition(
            identity=identity,
            condition_id=condition_id,
            new_state=ConditionState.EXPIRED,
            reason=reason,
            request_id=request_id,
            action="evidence.condition.expire",
        )

    def create_precheck(
        self, *, identity: IdentityContext, decision_unit_id: UUID, request_id: str
    ) -> PrecheckAssessment:
        _assert_unit(identity, decision_unit_id)
        now = self.clock.now()
        requirements = self.repository.list_requirements(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )
        matches = self.repository.list_matches(scope=identity.scope, decision_unit_id=decision_unit_id)
        profiles = self.repository.list_profiles(scope=identity.scope, decision_unit_id=decision_unit_id)
        conditions = self.repository.list_conditions(scope=identity.scope, decision_unit_id=decision_unit_id)
        match_by_requirement = {
            item.requirement_id: item
            for item in matches
            if item.validity_state is ValidityState.CURRENT
        }
        published_mandatory = [
            item
            for item in requirements
            if item.mandatory and formal_input_allowed(item, now=now).allowed
        ]
        unmapped = [item for item in published_mandatory if item.requirement_id not in match_by_requirement]
        mapped_states = [
            match_by_requirement[item.requirement_id].state for item in published_mandatory if item.requirement_id in match_by_requirement
        ]
        if unmapped:
            evidence_coverage = MatchState.UNKNOWN
        elif not published_mandatory:
            evidence_coverage = MatchState.UNKNOWN
        elif any(state is MatchState.UNSATISFIED for state in mapped_states):
            evidence_coverage = MatchState.UNSATISFIED
        elif any(state in {MatchState.UNKNOWN, MatchState.PARTIAL} for state in mapped_states):
            evidence_coverage = MatchState.PARTIAL if MatchState.PARTIAL in mapped_states else MatchState.UNKNOWN
        else:
            evidence_coverage = MatchState.SATISFIED

        current_profile = next(
            (
                item
                for item in reversed(profiles)
                if formal_input_allowed(item, now=now).allowed and item.valid_from <= now < item.valid_to
            ),
            None,
        )
        substantive = MatchState.SATISFIED if current_profile is not None else MatchState.UNKNOWN
        subject_states = [
            match_by_requirement[item.requirement_id].state
            for item in published_mandatory
            if item.requirement_id in match_by_requirement
        ]
        subject_qualification = (
            MatchState.SATISFIED
            if subject_states and all(state is MatchState.SATISFIED for state in subject_states)
            else evidence_coverage
        )
        rule_set = self.rule_availability_port.current_supported_rule_set(
            scope=identity.scope, decision_unit_id=decision_unit_id
        )
        rules_available = None if rule_set is None else bool(rule_set.supported and rule_set.current)
        open_blocking = [
            item.condition_id
            for item in conditions
            if condition_is_blocking(item, now=now)
        ]
        deadline_closure = not open_blocking
        checks = (
            PrecheckCheck(code="rules_available", passed=rules_available, reason_code="RULES_PORT" if rules_available is None else "OK"),
            PrecheckCheck(code="subject_qualification", passed=subject_qualification is MatchState.SATISFIED, reason_code=subject_qualification.value),
            PrecheckCheck(code="substantive_response", passed=substantive is MatchState.SATISFIED, reason_code=substantive.value),
            PrecheckCheck(code="evidence_coverage", passed=evidence_coverage is MatchState.SATISFIED, reason_code=evidence_coverage.value),
            PrecheckCheck(code="deadline_closure", passed=deadline_closure, reason_code="OPEN_CONDITIONS" if not deadline_closure else "OK"),
        )
        if rules_available is None or evidence_coverage is MatchState.UNKNOWN or not published_mandatory:
            decision = PrecheckDecision.UNKNOWN
        elif evidence_coverage is MatchState.UNSATISFIED or rules_available is False or not deadline_closure:
            decision = PrecheckDecision.BLOCKED
        elif evidence_coverage is MatchState.PARTIAL or substantive is not MatchState.SATISFIED:
            decision = PrecheckDecision.CONDITIONAL
        else:
            decision = PrecheckDecision.PASS
        item = PrecheckAssessment(
            precheck_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=_project_id(identity),
            decision_unit_id=decision_unit_id,
            decision=decision,
            validity_state=ValidityState.CURRENT,
            rules_available=rules_available,
            subject_qualification=subject_qualification,
            substantive_response=substantive,
            evidence_coverage=evidence_coverage,
            deadline_closure=deadline_closure,
            unmapped_mandatory_count=len(unmapped),
            condition_ids=tuple(open_blocking),
            checks=checks,
            created_at=now,
            created_by=identity.subject_id,
        )
        self.repository.upsert_precheck(item)
        self._audit(
            identity=identity,
            action="evidence.precheck.create",
            object_type="PrecheckAssessment",
            object_id=item.precheck_id,
            request_id=request_id,
            reason_code="PRECHECK_ASSESSED",
            outcome=item.decision.value,
            object_version_id=item.version_id,
        )
        _emit_event(
            self.outbox_port,
            identity=identity,
            event_type="evidence_commercial.precheck_assessed.v1",
            aggregate_type="PrecheckAssessment",
            aggregate_id=item.precheck_id,
            payload={
                "precheck_id": str(item.precheck_id),
                "decision": item.decision.value,
                "unmapped_mandatory_count": item.unmapped_mandatory_count,
            },
            request_id=request_id,
        )
        return item

    def list_prechecks(self, *, identity: IdentityContext, decision_unit_id: UUID) -> tuple[PrecheckAssessment, ...]:
        _assert_unit(identity, decision_unit_id)
        return self.repository.list_prechecks(scope=identity.scope, decision_unit_id=decision_unit_id)

    def get_precheck(self, *, identity: IdentityContext, precheck_id: UUID) -> PrecheckAssessment:
        item = self.repository.get_precheck(scope=identity.scope, precheck_id=precheck_id)
        if item is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def current_view(self, *, scope, decision_unit_id: UUID) -> EvidenceReadinessView:
        return self.readiness_view(scope=scope, decision_unit_id=decision_unit_id)

    def readiness_view(self, *, scope, decision_unit_id: UUID) -> EvidenceReadinessView:
        now = self.clock.now()
        prechecks = self.repository.list_prechecks(scope=scope, decision_unit_id=decision_unit_id)
        current = next((item for item in reversed(prechecks) if item.validity_state is ValidityState.CURRENT), None)
        profiles = self.repository.list_profiles(scope=scope, decision_unit_id=decision_unit_id)
        response_current = any(
            formal_input_allowed(item, now=now).allowed and item.valid_from <= now < item.valid_to
            for item in profiles
        )
        conditions = self.repository.list_conditions(scope=scope, decision_unit_id=decision_unit_id)
        return EvidenceReadinessView(
            precheck_decision=None if current is None else current.decision,
            precheck_validity=None if current is None else current.validity_state,
            response_profile_current=response_current,
            subject_qualification=None if current is None else current.subject_qualification,
            unmapped_mandatory_count=0 if current is None else current.unmapped_mandatory_count,
            open_blocking_condition_count=sum(1 for item in conditions if condition_is_blocking(item, now=now)),
        )


class EvidenceServices:
    def __init__(
        self,
        *,
        repository: EvidenceRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        outbox_port: OutboxPort | None,
        document_read_port: DocumentReadPort,
        rule_availability_port: RuleAvailabilityPort,
    ) -> None:
        self.repository = repository
        self.evidence = EvidenceService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
            outbox_port=outbox_port,
            document_read_port=document_read_port,
            rule_availability_port=rule_availability_port,
        )


def configure_evidence(
    app,
    *,
    repository: EvidenceRepository | None = None,
    document_read_port: DocumentReadPort | None = None,
    rule_availability_port: RuleAvailabilityPort | None = None,
) -> EvidenceServices:
    repository = repository or InMemoryEvidenceRepository()
    services = EvidenceServices(
        repository=repository,
        clock=SystemClock(),
        audit_writer=app.state.audit_writer,
        outbox_port=getattr(app.state, "outbox_port", None),
        document_read_port=document_read_port
        or getattr(app.state, "document_read_port", None)
        or UnavailableDocumentReadPort(),
        rule_availability_port=rule_availability_port
        or getattr(app.state, "rule_availability_port", None)
        or UnavailableRuleAvailabilityPort(),
    )
    app.state.evidence_repository = repository
    app.state.evidence_services = services
    app.state.condition_command_port = services.evidence
    app.state.evidence_readiness_port = services.evidence
    return services
