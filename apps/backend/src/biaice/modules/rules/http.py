"""FR-01 member-2 scope, regime, rule and compliance router."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from biaice.core.auth import IdentityContext
from biaice.core.errors import PROBLEM_RESPONSES
from biaice.core.http import CursorCodec, require_if_match
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.projects.application.authz import Fr01Guard
from biaice.modules.projects.application.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    paginate,
)
from biaice.modules.rules.application.services import (
    ApplicableRegimeService,
    ComplianceReviewService,
    CrossLotConstraintService,
    RuleClauseService,
    RuleSetService,
    RulesServices,
    ScopeAssessmentService,
)
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

router = APIRouter(prefix="/api/v1", tags=["rules"])


def _datetime_input(value: Any) -> Any:
    if isinstance(value, (str, datetime)):
        return value
    raise ValueError("datetime must be an ISO-8601 string")


StrictDateTime = Annotated[datetime, BeforeValidator(_datetime_input)]


def get_rules_services(request: Request) -> RulesServices:
    services = getattr(request.app.state, "rules_services", None)
    if services is None:
        from biaice.core.errors import BiaiceError

        raise BiaiceError("INTERNAL_ERROR", detail="FR-01 rule services are not configured.")
    return services


def get_scope_service(request: Request) -> ScopeAssessmentService:
    return get_rules_services(request).scope


def get_regime_service(request: Request) -> ApplicableRegimeService:
    return get_rules_services(request).regimes


def get_rule_set_service(request: Request) -> RuleSetService:
    return get_rules_services(request).rule_sets


def get_clause_service(request: Request) -> RuleClauseService:
    return get_rules_services(request).clauses


def get_review_service(request: Request) -> ComplianceReviewService:
    return get_rules_services(request).reviews


def get_cross_lot_service(request: Request) -> CrossLotConstraintService:
    return get_rules_services(request).cross_lot


def _cursor_codec(request: Request) -> CursorCodec | None:
    return getattr(request.app.state, "cursor_codec", None)


class ScopeWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    support: ScopeSupport
    round_kind: RoundKind
    cross_lot: bool = False
    reason_codes: tuple[str, ...] = ()
    source: SourceLocator | None = None
    applicability: str | None = Field(default=None, max_length=2000)


class ScopeDraftPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    support: ScopeSupport | None = None
    round_kind: RoundKind | None = None
    cross_lot: bool | None = None
    reason_codes: tuple[str, ...] | None = None
    applicability: str | None = Field(default=None, max_length=2000)


class RegimeWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    regime_name: str = Field(min_length=1, max_length=200)
    procurement_mode: ProcurementMode
    evaluation_method: EvaluationMethod
    round_kind: RoundKind
    source: SourceLocator | None = None


class RuleSetWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    scope_level: RuleScopeLevel = RuleScopeLevel.DECISION_UNIT
    effective_from: StrictDateTime | None = None
    effective_until: StrictDateTime | None = None


class ClauseWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: RuleClauseKind
    coverage_key: str = Field(min_length=1, max_length=120)
    priority: int = Field(ge=1, le=1000)
    original_text: str = Field(min_length=1, max_length=8000)
    structured_expression: str | None = Field(default=None, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    source: SourceLocator | None = None


class ClauseDraftPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_text: str | None = Field(default=None, min_length=1, max_length=8000)
    structured_expression: str | None = Field(default=None, max_length=4000)
    priority: int | None = Field(default=None, ge=1, le=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)


class ClauseSupersedeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_text: str = Field(min_length=1, max_length=8000)
    structured_expression: str | None = Field(default=None, max_length=4000)


class ReviewWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding: str = Field(min_length=1, max_length=4000)
    blocking: bool = False


class ReviewTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: ComplianceReviewState


class CrossLotWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    related_unit_ids: tuple[UUID, ...] = ()
    description: str = Field(min_length=1, max_length=2000)


class ScopeListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ScopeAssessment, ...]
    next_cursor: str | None = None
    has_more: bool = False


class RegimeListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ApplicableRegime, ...]
    next_cursor: str | None = None
    has_more: bool = False


class RuleSetListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[RuleSet, ...]
    next_cursor: str | None = None
    has_more: bool = False


class ClauseListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[RuleClause, ...]
    next_cursor: str | None = None
    has_more: bool = False


class ReviewListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[ComplianceReview, ...]
    next_cursor: str | None = None
    has_more: bool = False


class CrossLotListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CrossLotConstraint, ...]
    next_cursor: str | None = None
    has_more: bool = False


class RuleResolutionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[RuleResolution, ...]
    next_cursor: str | None = None
    has_more: bool = False


@router.get(
    "/decision-units/{unit_id}/scope-assessments",
    operation_id="list_scope_assessments",
    response_model=ScopeListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_scope_assessments(
    request: Request,
    unit_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ScopeAssessmentService = Depends(get_scope_service),
) -> ScopeListResponse:
    items, next_cursor, has_more = paginate(
        service.list(identity=identity, unit_id=unit_id),
        scope=identity.scope,
        codec=_cursor_codec(request),
        cursor=cursor,
        limit=limit,
        sort_key=lambda item: item.version.created_at.isoformat(),
        tie_breaker=lambda item: str(item.scope_assessment_id),
    )
    return ScopeListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/decision-units/{unit_id}/scope-assessments",
    operation_id="create_scope_assessment",
    response_model=ScopeAssessment,
    responses=PROBLEM_RESPONSES,
)
def create_scope_assessment(
    body: ScopeWriteRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ScopeAssessmentService = Depends(get_scope_service),
) -> ScopeAssessment:
    del idempotency_key
    return service.create(
        identity=identity,
        unit_id=unit_id,
        support=body.support,
        round_kind=body.round_kind,
        cross_lot=body.cross_lot,
        reason_codes=body.reason_codes,
        source=body.source,
        applicability=body.applicability,
        request_id=request.state.request_id,
    )


@router.get(
    "/scope-assessments/{scope_assessment_id}",
    operation_id="get_scope_assessment",
    response_model=ScopeAssessment,
    responses=PROBLEM_RESPONSES,
)
def get_scope_assessment(
    scope_assessment_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ScopeAssessmentService = Depends(get_scope_service),
) -> ScopeAssessment:
    return service.get(identity=identity, scope_assessment_id=scope_assessment_id)


@router.patch(
    "/scope-assessments/{scope_assessment_id}",
    operation_id="update_scope_assessment_draft",
    response_model=ScopeAssessment,
    responses=PROBLEM_RESPONSES,
)
def update_scope_assessment_draft(
    body: ScopeDraftPatchRequest,
    request: Request,
    scope_assessment_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    if_match: str = Depends(require_if_match),
    service: ScopeAssessmentService = Depends(get_scope_service),
) -> ScopeAssessment:
    return service.update_draft(
        identity=identity,
        scope_assessment_id=scope_assessment_id,
        if_match=if_match,
        support=body.support,
        round_kind=body.round_kind,
        cross_lot=body.cross_lot,
        reason_codes=body.reason_codes,
        applicability=body.applicability,
        request_id=request.state.request_id,
    )


@router.post(
    "/scope-assessments/{scope_assessment_id}/publish",
    operation_id="publish_scope_assessment",
    response_model=ScopeAssessment,
    responses=PROBLEM_RESPONSES,
)
def publish_scope_assessment(
    request: Request,
    scope_assessment_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(publish=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ScopeAssessmentService = Depends(get_scope_service),
) -> ScopeAssessment:
    del idempotency_key
    return service.publish(
        identity=identity,
        scope_assessment_id=scope_assessment_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/applicable-regimes",
    operation_id="list_applicable_regimes",
    response_model=RegimeListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_applicable_regimes(
    request: Request,
    unit_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ApplicableRegimeService = Depends(get_regime_service),
) -> RegimeListResponse:
    items, next_cursor, has_more = paginate(
        service.list(identity=identity, unit_id=unit_id),
        scope=identity.scope,
        codec=_cursor_codec(request),
        cursor=cursor,
        limit=limit,
        sort_key=lambda item: item.version.created_at.isoformat(),
        tie_breaker=lambda item: str(item.applicable_regime_id),
    )
    return RegimeListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/decision-units/{unit_id}/applicable-regimes",
    operation_id="create_applicable_regime",
    response_model=ApplicableRegime,
    responses=PROBLEM_RESPONSES,
)
def create_applicable_regime(
    body: RegimeWriteRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ApplicableRegimeService = Depends(get_regime_service),
) -> ApplicableRegime:
    del idempotency_key
    return service.create(
        identity=identity,
        unit_id=unit_id,
        regime_name=body.regime_name,
        procurement_mode=body.procurement_mode,
        evaluation_method=body.evaluation_method,
        round_kind=body.round_kind,
        source=body.source,
        request_id=request.state.request_id,
    )


@router.get(
    "/applicable-regimes/{applicable_regime_id}",
    operation_id="get_applicable_regime",
    response_model=ApplicableRegime,
    responses=PROBLEM_RESPONSES,
)
def get_applicable_regime(
    applicable_regime_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ApplicableRegimeService = Depends(get_regime_service),
) -> ApplicableRegime:
    return service.get(identity=identity, applicable_regime_id=applicable_regime_id)


@router.post(
    "/applicable-regimes/{applicable_regime_id}/publish",
    operation_id="publish_applicable_regime",
    response_model=ApplicableRegime,
    responses=PROBLEM_RESPONSES,
)
def publish_applicable_regime(
    request: Request,
    applicable_regime_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(publish=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ApplicableRegimeService = Depends(get_regime_service),
) -> ApplicableRegime:
    del idempotency_key
    return service.publish(
        identity=identity,
        applicable_regime_id=applicable_regime_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/rule-sets",
    operation_id="list_rule_sets",
    response_model=RuleSetListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_rule_sets(
    request: Request,
    unit_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: RuleSetService = Depends(get_rule_set_service),
) -> RuleSetListResponse:
    items, next_cursor, has_more = paginate(
        service.list(identity=identity, unit_id=unit_id),
        scope=identity.scope,
        codec=_cursor_codec(request),
        cursor=cursor,
        limit=limit,
        sort_key=lambda item: item.version.created_at.isoformat(),
        tie_breaker=lambda item: str(item.rule_set_id),
    )
    return RuleSetListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/decision-units/{unit_id}/rule-sets",
    operation_id="create_rule_set",
    response_model=RuleSet,
    responses=PROBLEM_RESPONSES,
)
def create_rule_set(
    body: RuleSetWriteRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: RuleSetService = Depends(get_rule_set_service),
) -> RuleSet:
    del idempotency_key
    return service.create(
        identity=identity,
        unit_id=unit_id,
        title=body.title,
        scope_level=body.scope_level,
        effective_from=body.effective_from,
        effective_until=body.effective_until,
        request_id=request.state.request_id,
    )


@router.get(
    "/rule-sets/{rule_set_id}",
    operation_id="get_rule_set",
    response_model=RuleSet,
    responses=PROBLEM_RESPONSES,
)
def get_rule_set(
    rule_set_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: RuleSetService = Depends(get_rule_set_service),
) -> RuleSet:
    return service.get(identity=identity, rule_set_id=rule_set_id)


@router.post(
    "/rule-sets/{rule_set_id}/publish",
    operation_id="publish_rule_set",
    response_model=RuleSet,
    responses=PROBLEM_RESPONSES,
)
def publish_rule_set(
    request: Request,
    rule_set_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(publish=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: RuleSetService = Depends(get_rule_set_service),
) -> RuleSet:
    del idempotency_key
    return service.publish(
        identity=identity, rule_set_id=rule_set_id, request_id=request.state.request_id
    )


@router.get(
    "/rule-sets/{rule_set_id}/clauses",
    operation_id="list_rule_clauses",
    response_model=ClauseListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_rule_clauses(
    request: Request,
    rule_set_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: RuleClauseService = Depends(get_clause_service),
) -> ClauseListResponse:
    items, next_cursor, has_more = paginate(
        service.list(identity=identity, rule_set_id=rule_set_id),
        scope=identity.scope,
        codec=_cursor_codec(request),
        cursor=cursor,
        limit=limit,
        sort_key=lambda item: f"{item.priority:04d}",
        tie_breaker=lambda item: str(item.rule_clause_id),
    )
    return ClauseListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/rule-sets/{rule_set_id}/clauses",
    operation_id="create_rule_clause",
    response_model=RuleClause,
    responses=PROBLEM_RESPONSES,
)
def create_rule_clause(
    body: ClauseWriteRequest,
    request: Request,
    rule_set_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: RuleClauseService = Depends(get_clause_service),
) -> RuleClause:
    del idempotency_key
    return service.create(
        identity=identity,
        rule_set_id=rule_set_id,
        kind=body.kind,
        coverage_key=body.coverage_key,
        priority=body.priority,
        original_text=body.original_text,
        structured_expression=body.structured_expression,
        confidence=body.confidence,
        source=body.source,
        request_id=request.state.request_id,
    )


@router.get(
    "/rule-clauses/{rule_clause_id}",
    operation_id="get_rule_clause",
    response_model=RuleClause,
    responses=PROBLEM_RESPONSES,
)
def get_rule_clause(
    rule_clause_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: RuleClauseService = Depends(get_clause_service),
) -> RuleClause:
    return service.get(identity=identity, rule_clause_id=rule_clause_id)


@router.patch(
    "/rule-clauses/{rule_clause_id}",
    operation_id="update_rule_clause_draft",
    response_model=RuleClause,
    responses=PROBLEM_RESPONSES,
)
def update_rule_clause_draft(
    body: ClauseDraftPatchRequest,
    request: Request,
    rule_clause_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    if_match: str = Depends(require_if_match),
    service: RuleClauseService = Depends(get_clause_service),
) -> RuleClause:
    return service.update_draft(
        identity=identity,
        rule_clause_id=rule_clause_id,
        if_match=if_match,
        original_text=body.original_text,
        structured_expression=body.structured_expression,
        priority=body.priority,
        confidence=body.confidence,
        request_id=request.state.request_id,
    )


@router.post(
    "/rule-clauses/{rule_clause_id}/supersede",
    operation_id="supersede_rule_clause",
    response_model=RuleClause,
    responses=PROBLEM_RESPONSES,
)
def supersede_rule_clause(
    body: ClauseSupersedeRequest,
    request: Request,
    rule_clause_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: RuleClauseService = Depends(get_clause_service),
) -> RuleClause:
    del idempotency_key
    return service.supersede(
        identity=identity,
        rule_clause_id=rule_clause_id,
        original_text=body.original_text,
        structured_expression=body.structured_expression,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/compliance-reviews",
    operation_id="list_compliance_reviews",
    response_model=ReviewListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_compliance_reviews(
    request: Request,
    unit_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ComplianceReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    items, next_cursor, has_more = paginate(
        service.list(identity=identity, unit_id=unit_id),
        scope=identity.scope,
        codec=_cursor_codec(request),
        cursor=cursor,
        limit=limit,
        sort_key=lambda item: item.version.created_at.isoformat(),
        tie_breaker=lambda item: str(item.compliance_review_id),
    )
    return ReviewListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/decision-units/{unit_id}/compliance-reviews",
    operation_id="create_compliance_review",
    response_model=ComplianceReview,
    responses=PROBLEM_RESPONSES,
)
def create_compliance_review(
    body: ReviewWriteRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ComplianceReviewService = Depends(get_review_service),
) -> ComplianceReview:
    del idempotency_key
    return service.create(
        identity=identity,
        unit_id=unit_id,
        finding=body.finding,
        blocking=body.blocking,
        request_id=request.state.request_id,
    )


@router.get(
    "/compliance-reviews/{compliance_review_id}",
    operation_id="get_compliance_review",
    response_model=ComplianceReview,
    responses=PROBLEM_RESPONSES,
)
def get_compliance_review(
    compliance_review_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: ComplianceReviewService = Depends(get_review_service),
) -> ComplianceReview:
    return service.get(identity=identity, compliance_review_id=compliance_review_id)


@router.post(
    "/compliance-reviews/{compliance_review_id}/transition",
    operation_id="transition_compliance_review",
    response_model=ComplianceReview,
    responses=PROBLEM_RESPONSES,
)
def transition_compliance_review(
    body: ReviewTransitionRequest,
    request: Request,
    compliance_review_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ComplianceReviewService = Depends(get_review_service),
) -> ComplianceReview:
    del idempotency_key
    return service.transition(
        identity=identity,
        compliance_review_id=compliance_review_id,
        target=body.target,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/cross-lot-constraints",
    operation_id="list_cross_lot_constraints",
    response_model=CrossLotListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_cross_lot_constraints(
    request: Request,
    unit_id: UUID,
    cursor: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    identity: IdentityContext = Depends(Fr01Guard()),
    service: CrossLotConstraintService = Depends(get_cross_lot_service),
) -> CrossLotListResponse:
    items, next_cursor, has_more = paginate(
        service.list(identity=identity, unit_id=unit_id),
        scope=identity.scope,
        codec=_cursor_codec(request),
        cursor=cursor,
        limit=limit,
        sort_key=lambda item: item.version.created_at.isoformat(),
        tie_breaker=lambda item: str(item.cross_lot_constraint_id),
    )
    return CrossLotListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post(
    "/decision-units/{unit_id}/cross-lot-constraints",
    operation_id="create_cross_lot_constraint",
    response_model=CrossLotConstraint,
    responses=PROBLEM_RESPONSES,
)
def create_cross_lot_constraint(
    body: CrossLotWriteRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CrossLotConstraintService = Depends(get_cross_lot_service),
) -> CrossLotConstraint:
    del idempotency_key
    return service.create(
        identity=identity,
        unit_id=unit_id,
        related_unit_ids=body.related_unit_ids,
        description=body.description,
        request_id=request.state.request_id,
    )


@router.get(
    "/cross-lot-constraints/{cross_lot_constraint_id}",
    operation_id="get_cross_lot_constraint",
    response_model=CrossLotConstraint,
    responses=PROBLEM_RESPONSES,
)
def get_cross_lot_constraint(
    cross_lot_constraint_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: CrossLotConstraintService = Depends(get_cross_lot_service),
) -> CrossLotConstraint:
    return service.get(identity=identity, cross_lot_constraint_id=cross_lot_constraint_id)


@router.post(
    "/cross-lot-constraints/{cross_lot_constraint_id}/confirm",
    operation_id="confirm_cross_lot_constraint",
    response_model=CrossLotConstraint,
    responses=PROBLEM_RESPONSES,
)
def confirm_cross_lot_constraint(
    request: Request,
    cross_lot_constraint_id: UUID,
    identity: IdentityContext = Depends(Fr01Guard(write=True, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: CrossLotConstraintService = Depends(get_cross_lot_service),
) -> CrossLotConstraint:
    del idempotency_key
    return service.confirm(
        identity=identity,
        cross_lot_constraint_id=cross_lot_constraint_id,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/rule-resolutions",
    operation_id="list_rule_resolutions",
    response_model=RuleResolutionListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_rule_resolutions(
    unit_id: UUID,
    formal: bool = True,
    identity: IdentityContext = Depends(Fr01Guard()),
    service: RuleClauseService = Depends(get_clause_service),
) -> RuleResolutionListResponse:
    items = service.resolve_unit(identity=identity, unit_id=unit_id, formal=formal)
    return RuleResolutionListResponse(items=items, next_cursor=None, has_more=False)
