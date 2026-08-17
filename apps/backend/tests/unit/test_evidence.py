"""Unit tests for member-4 FR-03 evidence, match, precheck and conditions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.errors import BiaiceError
from biaice.modules.evidence.application.ports import UnavailableDocumentReadPort
from biaice.modules.evidence.application.repository import InMemoryEvidenceRepository
from biaice.modules.evidence.application.services import EvidenceService
from biaice.modules.evidence.domain.models import (
    BlockingStage,
    EvidenceCategory,
    LifecycleState,
    MatchState,
    PrecheckDecision,
)

TENANT = uuid4()
DOMAIN = uuid4()
UNIT = uuid4()
ACTOR = uuid4()
REVIEWER = uuid4()
NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class ReleasedDocument:
    def __init__(self, document_id, content_hash="a" * 64) -> None:
        self.document_id = document_id
        self.content_hash = content_hash
        self.status = "RELEASED"
        self.parse_status = "SUCCEEDED"
        self.fragment_refs = ("page:1",)


class FakeDocumentPort:
    def __init__(self, released=()) -> None:
        self._released = {item.document_id: item for item in released}

    def get_released_document(self, *, scope, document_id):
        del scope
        return self._released.get(document_id)


def _identity(*, actor=ACTOR, tenant=TENANT, roles=None):
    return IdentityContext(
        subject_id=actor,
        username="m4",
        display_name="Member Four",
        roles=frozenset(roles or {Role.DOCUMENT_SPECIALIST, Role.DOCUMENT_STEWARD}),
        scope=TenantScope(
            tenant_id=tenant,
            data_domain_id=DOMAIN,
            all_decision_units=True,
        ),
        mfa_verified=True,
        authenticated_at=NOW,
    )


def _service(document_port=None):
    sink = InMemoryAppendOnlyAuditSink()
    audit = HashChainAuditWriter(sink, clock=FixedClock(NOW))
    service = EvidenceService(
        repository=InMemoryEvidenceRepository(),
        clock=FixedClock(NOW),
        audit_writer=audit,
        outbox_port=None,
        document_read_port=document_port or UnavailableDocumentReadPort(),
        rule_availability_port=type(
            "NoRules",
            (),
            {"current_supported_rule_set": staticmethod(lambda **kwargs: None)},
        )(),
    )
    return service, sink


def test_unmapped_mandatory_requirement_makes_precheck_unknown() -> None:
    service, _ = _service()
    identity = _identity()
    requirement = service.create_requirement(
        identity=identity,
        decision_unit_id=UNIT,
        title="ISO 9001",
        statement="Must hold a valid quality system certificate.",
        mandatory=True,
        rule_clause_id=None,
        source_document_id=None,
        source_page=None,
        source_section=None,
        request_id="req-1",
    )
    service.publish_requirement(
        identity=identity, requirement_id=requirement.requirement_id, request_id="req-2"
    )
    precheck = service.create_precheck(identity=identity, decision_unit_id=UNIT, request_id="req-3")
    assert precheck.unmapped_mandatory_count == 1
    assert precheck.decision is PrecheckDecision.UNKNOWN
    assert precheck.evidence_coverage is MatchState.UNKNOWN


def test_match_without_evidence_cannot_be_satisfied() -> None:
    service, _ = _service()
    identity = _identity()
    requirement = service.create_requirement(
        identity=identity,
        decision_unit_id=UNIT,
        title="License",
        statement="Construction license required.",
        mandatory=True,
        rule_clause_id=None,
        source_document_id=None,
        source_page=None,
        source_section=None,
        request_id="req-1",
    )
    with pytest.raises(BiaiceError) as error:
        service.create_match(
            identity=identity,
            decision_unit_id=UNIT,
            requirement_id=requirement.requirement_id,
            evidence_id=None,
            requested_state=MatchState.SATISFIED,
            rationale="no file but mark satisfied",
            request_id="req-2",
        )
    assert error.value.code == "WAIVER_PROHIBITED"
    assert error.value.detail == "EVIDENCE_SATISFIED_WITHOUT_PROOF"


def test_unknown_document_citation_is_fail_closed() -> None:
    service, _ = _service()
    with pytest.raises(BiaiceError) as error:
        service.create_evidence(
            identity=_identity(),
            decision_unit_id=UNIT,
            category=EvidenceCategory.QUALIFICATION,
            subject="Our company",
            summary="Certificate",
            source="internal archive",
            source_document_id=uuid4(),
            fragment_ref="page:1",
            valid_from=NOW - timedelta(days=1),
            valid_to=NOW + timedelta(days=365),
            request_id="req-1",
        )
    assert error.value.code == "DOCUMENT_NOT_DOWNLOADABLE"
    assert error.value.detail == "EVIDENCE_DOCUMENT_NOT_RELEASED"


def test_released_document_hash_is_copied_and_evidence_can_publish() -> None:
    document_id = uuid4()
    service, sink = _service(FakeDocumentPort([ReleasedDocument(document_id)]))
    author = _identity()
    evidence = service.create_evidence(
        identity=author,
        decision_unit_id=UNIT,
        category=EvidenceCategory.QUALIFICATION,
        subject="Our company",
        summary="Certificate",
        source="member-3 released document",
        source_document_id=document_id,
        fragment_ref="page:1",
        valid_from=NOW - timedelta(days=1),
        valid_to=NOW + timedelta(days=365),
        request_id="req-1",
    )
    assert evidence.content_hash == "a" * 64
    with pytest.raises(BiaiceError) as error:
        service.review_evidence(
            identity=author, evidence_id=evidence.evidence_id, request_id="req-2"
        )
    assert error.value.code == "MAKER_CHECKER_REQUIRED"
    reviewed = service.review_evidence(
        identity=_identity(actor=REVIEWER),
        evidence_id=evidence.evidence_id,
        request_id="req-3",
    )
    published = service.publish_evidence(
        identity=author, evidence_id=reviewed.evidence_id, request_id="req-4"
    )
    assert published.lifecycle_state is LifecycleState.PUBLISHED
    actions = [event.action for event in sink.list_events(author.scope)]
    assert "evidence.evidence.publish" in actions


def test_revoke_propagates_only_to_dependent_matches() -> None:
    document_id = uuid4()
    service, _ = _service(FakeDocumentPort([ReleasedDocument(document_id)]))
    author = _identity()
    requirement = service.create_requirement(
        identity=author,
        decision_unit_id=UNIT,
        title="License",
        statement="Hold license",
        mandatory=True,
        rule_clause_id=None,
        source_document_id=None,
        source_page=None,
        source_section=None,
        request_id="r1",
    )
    evidence = service.create_evidence(
        identity=author,
        decision_unit_id=UNIT,
        category=EvidenceCategory.QUALIFICATION,
        subject="Our company",
        summary="Certificate",
        source="released",
        source_document_id=document_id,
        fragment_ref=None,
        valid_from=NOW - timedelta(days=1),
        valid_to=NOW + timedelta(days=30),
        request_id="r2",
    )
    service.review_evidence(
        identity=_identity(actor=REVIEWER), evidence_id=evidence.evidence_id, request_id="r3"
    )
    published = service.publish_evidence(
        identity=author, evidence_id=evidence.evidence_id, request_id="r4"
    )
    match = service.create_match(
        identity=author,
        decision_unit_id=UNIT,
        requirement_id=requirement.requirement_id,
        evidence_id=published.evidence_id,
        requested_state=MatchState.SATISFIED,
        rationale="certificate covers the clause",
        request_id="r5",
    )
    assert match.state is MatchState.SATISFIED
    service.revoke_evidence(
        identity=author,
        evidence_id=published.evidence_id,
        reason="expired in registry",
        request_id="r6",
    )
    stale = service.get_match(identity=author, match_id=match.match_id)
    assert stale.state is MatchState.UNKNOWN


def test_condition_command_port_is_append_only() -> None:
    service, _ = _service()
    owner = uuid4()
    reviewer = uuid4()
    condition = service.create_condition(
        identity=_identity(),
        decision_unit_id=UNIT,
        title="Supplement personnel resume",
        statement="Provide independent reviewer pack",
        owner_id=owner,
        independent_reviewer_id=reviewer,
        evidence_id=None,
        due_at=NOW + timedelta(days=7),
        blocking_stage=BlockingStage.APPROVAL,
        request_id="c1",
    )
    closed = service.satisfy_condition(
        identity=_identity(actor=REVIEWER),
        condition_id=condition.condition_id,
        reason="resume uploaded and reviewed",
        request_id="c2",
    )
    assert closed.state.value == "SATISFIED"
    with pytest.raises(BiaiceError) as error:
        service.waive_condition(
            identity=_identity(actor=REVIEWER),
            condition_id=condition.condition_id,
            reason="again",
            request_id="c3",
        )
    assert error.value.code == "JOB_NOT_CANCELLABLE"
    assert error.value.detail == "CONDITION_NOT_OPEN"


def test_scope_hides_other_tenant_evidence() -> None:
    service, _ = _service()
    item = service.create_requirement(
        identity=_identity(),
        decision_unit_id=UNIT,
        title="A",
        statement="A statement",
        mandatory=False,
        rule_clause_id=None,
        source_document_id=None,
        source_page=None,
        source_section=None,
        request_id="s1",
    )
    with pytest.raises(BiaiceError) as error:
        service.get_requirement(
            identity=_identity(tenant=uuid4()),
            requirement_id=item.requirement_id,
        )
    assert error.value.code == "RESOURCE_NOT_FOUND"
