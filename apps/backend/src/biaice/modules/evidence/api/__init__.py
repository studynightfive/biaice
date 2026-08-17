"""FR-03 FastAPI router. operationIds match the frozen P0 catalog including stub typos."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.http import require_if_match
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.evidence.application.services import EvidenceService, EvidenceServices
from biaice.modules.evidence.domain.models import (
    BlockingStage,
    CompanyEvidence,
    CompanyResponseProfile,
    ConditionRequirement,
    EvidenceCategory,
    EvidenceMatch,
    MatchState,
    PrecheckAssessment,
    Requirement,
)

router = APIRouter(prefix="/api/v1", tags=["evidence"])


def _datetime_input(value: Any) -> Any:
    if isinstance(value, (str, datetime)):
        return value
    raise ValueError("datetime must be an ISO-8601 string")


StrictDateTime = Annotated[datetime, BeforeValidator(_datetime_input)]


def get_evidence_services(request: Request) -> EvidenceServices:
    services = getattr(request.app.state, "evidence_services", None)
    if services is None:
        raise BiaiceError("INTERNAL_ERROR", detail="Evidence services are not configured.")
    return services


def get_service(request: Request) -> EvidenceService:
    return get_evidence_services(request).evidence


class ItemList(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RequirementListResponse(ItemList):
    items: tuple[Requirement, ...]


class EvidenceListResponse(ItemList):
    items: tuple[CompanyEvidence, ...]


class MatchListResponse(ItemList):
    items: tuple[EvidenceMatch, ...]


class ProfileListResponse(ItemList):
    items: tuple[CompanyResponseProfile, ...]


class PrecheckListResponse(ItemList):
    items: tuple[PrecheckAssessment, ...]


class ConditionListResponse(ItemList):
    items: tuple[ConditionRequirement, ...]


class CreateRequirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=4000)
    mandatory: bool = True
    rule_clause_id: UUID | None = None
    source_document_id: UUID | None = None
    source_page: str | None = Field(default=None, max_length=40)
    source_section: str | None = Field(default=None, max_length=120)


class UpdateRequirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=4000)
    mandatory: bool = True


class CreateEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: EvidenceCategory
    subject: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=400)
    source_document_id: UUID | None = None
    fragment_ref: str | None = Field(default=None, max_length=200)
    valid_from: StrictDateTime
    valid_to: StrictDateTime


class RevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


class CreateMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_id: UUID
    evidence_id: UUID | None = None
    state: MatchState = MatchState.UNKNOWN
    rationale: str = Field(min_length=1, max_length=2000)


class ReviewMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: MatchState
    rationale: str = Field(min_length=1, max_length=2000)


class CreateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qualification_preparation: str = Field(min_length=1, max_length=4000)
    technical_response: str = Field(min_length=1, max_length=4000)
    service_response: str = Field(min_length=1, max_length=4000)
    objective_non_price_inputs: dict[str, str] = Field(default_factory=dict)
    subjective_variable_intervals: dict[str, str] = Field(default_factory=dict)
    evidence_ids: tuple[UUID, ...] = ()
    valid_from: StrictDateTime
    valid_to: StrictDateTime


class CreateConditionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=2000)
    owner_id: UUID
    independent_reviewer_id: UUID
    evidence_id: UUID | None = None
    due_at: StrictDateTime
    blocking_stage: BlockingStage


class ConditionCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


def _extras(fr: str, permission: str) -> dict[str, Any]:
    return {
        "x-contract-only": False,
        "x-owner": "member-4",
        "x-fr": fr,
        "x-required-permission": permission,
        "x-schema-status": "OWNER_FROZEN",
    }


@router.get(
    "/decision-units/{unit_id}/requirements",
    operation_id="list_requirements",
    response_model=RequirementListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def list_requirements(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> RequirementListResponse:
    return RequirementListResponse(items=service.list_requirements(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/requirements",
    operation_id="create_requirement",
    response_model=Requirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:create"), "x-idempotency-required": True},
)
def create_requirement(
    body: CreateRequirementRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> Requirement:
    del idempotency_key
    return service.create_requirement(
        identity=identity,
        decision_unit_id=unit_id,
        title=body.title,
        statement=body.statement,
        mandatory=body.mandatory,
        rule_clause_id=body.rule_clause_id,
        source_document_id=body.source_document_id,
        source_page=body.source_page,
        source_section=body.source_section,
        request_id=request.state.request_id,
    )


@router.get(
    "/requirements/{requirement_id}",
    operation_id="get_requirement",
    response_model=Requirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def get_requirement(
    requirement_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> Requirement:
    return service.get_requirement(identity=identity, requirement_id=requirement_id)


@router.patch(
    "/requirements/{requirement_id}",
    operation_id="update_requirement_draft",
    response_model=Requirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:update"), "x-etag-required": True},
)
def update_requirement_draft(
    body: UpdateRequirementRequest,
    request: Request,
    requirement_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_UPDATE)),
    if_match: str = Depends(require_if_match),
    service: EvidenceService = Depends(get_service),
) -> Requirement:
    return service.update_requirement_draft(
        identity=identity,
        requirement_id=requirement_id,
        title=body.title,
        statement=body.statement,
        mandatory=body.mandatory,
        if_match=if_match,
        request_id=request.state.request_id,
    )


@router.post(
    "/requirements/{requirement_id}/publish",
    operation_id="publish_requirement",
    response_model=Requirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:publish"), "x-idempotency-required": True},
)
def publish_requirement(
    request: Request,
    requirement_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_PUBLISH, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> Requirement:
    del idempotency_key
    return service.publish_requirement(
        identity=identity, requirement_id=requirement_id, request_id=request.state.request_id
    )


@router.post(
    "/requirements/{requirement_id}/supersede",
    operation_id="supersede_requirement",
    response_model=Requirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:supersede"), "x-idempotency-required": True},
)
def supersede_requirement(
    request: Request,
    requirement_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_SUPERSEDE, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> Requirement:
    del idempotency_key
    return service.supersede_requirement(
        identity=identity, requirement_id=requirement_id, request_id=request.state.request_id
    )


@router.get(
    "/decision-units/{unit_id}/evidence",
    operation_id="list_evidence",
    response_model=EvidenceListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def list_evidence(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> EvidenceListResponse:
    return EvidenceListResponse(items=service.list_evidence(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/evidence",
    operation_id="create_evidence",
    response_model=CompanyEvidence,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:create"), "x-idempotency-required": True},
)
def create_evidence(
    body: CreateEvidenceRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> CompanyEvidence:
    del idempotency_key
    return service.create_evidence(
        identity=identity,
        decision_unit_id=unit_id,
        category=body.category,
        subject=body.subject,
        summary=body.summary,
        source=body.source,
        source_document_id=body.source_document_id,
        fragment_ref=body.fragment_ref,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        request_id=request.state.request_id,
    )


@router.get(
    "/evidence/{evidence_id}",
    operation_id="get_evidence",
    response_model=CompanyEvidence,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def get_evidence(
    evidence_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> CompanyEvidence:
    return service.get_evidence(identity=identity, evidence_id=evidence_id)


@router.post(
    "/evidence/{evidence_id}/review",
    operation_id="review_evidence",
    response_model=CompanyEvidence,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:review"), "x-idempotency-required": True},
)
def review_evidence(
    request: Request,
    evidence_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_REVIEW, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> CompanyEvidence:
    del idempotency_key
    return service.review_evidence(
        identity=identity, evidence_id=evidence_id, request_id=request.state.request_id
    )


@router.post(
    "/evidence/{evidence_id}/publish",
    operation_id="publish_evidence",
    response_model=CompanyEvidence,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:publish"), "x-idempotency-required": True},
)
def publish_evidence(
    request: Request,
    evidence_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_PUBLISH, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> CompanyEvidence:
    del idempotency_key
    return service.publish_evidence(
        identity=identity, evidence_id=evidence_id, request_id=request.state.request_id
    )


@router.post(
    "/evidence/{evidence_id}/revoke",
    operation_id="revoke_evidence",
    response_model=CompanyEvidence,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:revoke"), "x-idempotency-required": True},
)
def revoke_evidence(
    body: RevokeRequest,
    request: Request,
    evidence_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_REVOKE, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> CompanyEvidence:
    del idempotency_key
    return service.revoke_evidence(
        identity=identity,
        evidence_id=evidence_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/evidence-matches",
    operation_id="list_evidence_matches",
    response_model=MatchListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def list_evidence_matches(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> MatchListResponse:
    return MatchListResponse(items=service.list_matches(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/evidence-matches",
    operation_id="create_evidence_matche",
    response_model=EvidenceMatch,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:create"), "x-idempotency-required": True},
)
def create_evidence_matche(
    body: CreateMatchRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> EvidenceMatch:
    del idempotency_key
    return service.create_match(
        identity=identity,
        decision_unit_id=unit_id,
        requirement_id=body.requirement_id,
        evidence_id=body.evidence_id,
        requested_state=body.state,
        rationale=body.rationale,
        request_id=request.state.request_id,
    )


@router.get(
    "/evidence-matches/{evidence_matche_id}",
    operation_id="get_evidence_matche",
    response_model=EvidenceMatch,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def get_evidence_matche(
    evidence_matche_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> EvidenceMatch:
    return service.get_match(identity=identity, match_id=evidence_matche_id)


@router.post(
    "/evidence-matches/{evidence_match_id}/review",
    operation_id="review_evidence_match",
    response_model=EvidenceMatch,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:review"), "x-idempotency-required": True},
)
def review_evidence_match(
    body: ReviewMatchRequest,
    request: Request,
    evidence_match_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_REVIEW, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> EvidenceMatch:
    del idempotency_key
    return service.review_match(
        identity=identity,
        match_id=evidence_match_id,
        state=body.state,
        rationale=body.rationale,
        request_id=request.state.request_id,
    )


@router.get(
    "/decision-units/{unit_id}/response-profiles",
    operation_id="list_response_profiles",
    response_model=ProfileListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def list_response_profiles(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> ProfileListResponse:
    return ProfileListResponse(items=service.list_profiles(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/response-profiles",
    operation_id="create_response_profile",
    response_model=CompanyResponseProfile,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:create"), "x-idempotency-required": True},
)
def create_response_profile(
    body: CreateProfileRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> CompanyResponseProfile:
    del idempotency_key
    return service.create_profile(
        identity=identity,
        decision_unit_id=unit_id,
        qualification_preparation=body.qualification_preparation,
        technical_response=body.technical_response,
        service_response=body.service_response,
        objective_non_price_inputs=body.objective_non_price_inputs,
        subjective_variable_intervals=body.subjective_variable_intervals,
        evidence_ids=body.evidence_ids,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        request_id=request.state.request_id,
    )


@router.get(
    "/response-profiles/{response_profile_id}",
    operation_id="get_response_profile",
    response_model=CompanyResponseProfile,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def get_response_profile(
    response_profile_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> CompanyResponseProfile:
    return service.get_profile(identity=identity, profile_id=response_profile_id)


@router.post(
    "/response-profiles/{response_profile_id}/publish",
    operation_id="publish_response_profile",
    response_model=CompanyResponseProfile,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:publish"), "x-idempotency-required": True},
)
def publish_response_profile(
    request: Request,
    response_profile_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_PUBLISH, mfa=True)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> CompanyResponseProfile:
    del idempotency_key
    return service.publish_profile(
        identity=identity, profile_id=response_profile_id, request_id=request.state.request_id
    )


@router.get(
    "/decision-units/{unit_id}/precheck-assessments",
    operation_id="list_precheck_assessments",
    response_model=PrecheckListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def list_precheck_assessments(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> PrecheckListResponse:
    return PrecheckListResponse(items=service.list_prechecks(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/precheck-assessments",
    operation_id="create_precheck_assessment",
    response_model=PrecheckAssessment,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:create"), "x-idempotency-required": True},
)
def create_precheck_assessment(
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> PrecheckAssessment:
    del idempotency_key
    return service.create_precheck(
        identity=identity, decision_unit_id=unit_id, request_id=request.state.request_id
    )


@router.get(
    "/precheck-assessments/{precheck_assessment_id}",
    operation_id="get_precheck_assessment",
    response_model=PrecheckAssessment,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def get_precheck_assessment(
    precheck_assessment_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> PrecheckAssessment:
    return service.get_precheck(identity=identity, precheck_id=precheck_assessment_id)


@router.get(
    "/decision-units/{unit_id}/conditions",
    operation_id="list_conditions",
    response_model=ConditionListResponse,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def list_conditions(
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> ConditionListResponse:
    return ConditionListResponse(items=service.list_conditions(identity=identity, decision_unit_id=unit_id))


@router.post(
    "/decision-units/{unit_id}/conditions",
    operation_id="create_condition",
    response_model=ConditionRequirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:create"), "x-idempotency-required": True},
)
def create_condition(
    body: CreateConditionRequest,
    request: Request,
    unit_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_CREATE)),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> ConditionRequirement:
    del idempotency_key
    return service.create_condition(
        identity=identity,
        decision_unit_id=unit_id,
        title=body.title,
        statement=body.statement,
        owner_id=body.owner_id,
        independent_reviewer_id=body.independent_reviewer_id,
        evidence_id=body.evidence_id,
        due_at=body.due_at,
        blocking_stage=body.blocking_stage,
        request_id=request.state.request_id,
    )


@router.get(
    "/conditions/{condition_id}",
    operation_id="get_condition",
    response_model=ConditionRequirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extras("FR-03", "fr-03:read"),
)
def get_condition(
    condition_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.FR03_READ)),
    service: EvidenceService = Depends(get_service),
) -> ConditionRequirement:
    return service.get_condition(identity=identity, condition_id=condition_id)


def _condition_command(permission: Permission):
    return Depends(PermissionGuard(permission, mfa=True))


@router.post(
    "/conditions/{condition_id}/satisfy",
    operation_id="satisfy_condition",
    response_model=ConditionRequirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:satisfy"), "x-idempotency-required": True},
)
def satisfy_condition(
    body: ConditionCommandRequest,
    request: Request,
    condition_id: UUID,
    identity: IdentityContext = _condition_command(Permission.FR03_SATISFY),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> ConditionRequirement:
    del idempotency_key
    return service.satisfy_condition(
        identity=identity,
        condition_id=condition_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )


@router.post(
    "/conditions/{condition_id}/waive",
    operation_id="waive_condition",
    response_model=ConditionRequirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:waive"), "x-idempotency-required": True},
)
def waive_condition(
    body: ConditionCommandRequest,
    request: Request,
    condition_id: UUID,
    identity: IdentityContext = _condition_command(Permission.FR03_WAIVE),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> ConditionRequirement:
    del idempotency_key
    return service.waive_condition(
        identity=identity,
        condition_id=condition_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )


@router.post(
    "/conditions/{condition_id}/fail",
    operation_id="fail_condition",
    response_model=ConditionRequirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:fail"), "x-idempotency-required": True},
)
def fail_condition(
    body: ConditionCommandRequest,
    request: Request,
    condition_id: UUID,
    identity: IdentityContext = _condition_command(Permission.FR03_FAIL),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> ConditionRequirement:
    del idempotency_key
    return service.fail_condition(
        identity=identity,
        condition_id=condition_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )


@router.post(
    "/conditions/{condition_id}/expire",
    operation_id="expire_condition",
    response_model=ConditionRequirement,
    responses=PROBLEM_RESPONSES,
    openapi_extra={**_extras("FR-03", "fr-03:expire"), "x-idempotency-required": True},
)
def expire_condition(
    body: ConditionCommandRequest,
    request: Request,
    condition_id: UUID,
    identity: IdentityContext = _condition_command(Permission.FR03_EXPIRE),
    idempotency_key: str = Depends(require_idempotency_key),
    service: EvidenceService = Depends(get_service),
) -> ConditionRequirement:
    del idempotency_key
    return service.expire_condition(
        identity=identity,
        condition_id=condition_id,
        reason=body.reason,
        request_id=request.state.request_id,
    )
