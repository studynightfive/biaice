"""Typed FR-05 competitor and market-prior API."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Callable, Self, TypeVar
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.http import compute_etag, require_if_match
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.market.application.governance import (
    MarketGovernanceService,
    new_competitor,
)
from biaice.modules.market.domain.models import (
    Competitor,
    CompetitorProfile,
    CompetitorSource,
    DataClassification,
    MarketPriorVersion,
    SubjectDeduplicationRun,
    UnknownEntrantProfileVersion,
)

router = APIRouter(prefix="/api/v1", tags=["FR-05", "market"])

IDEMPOTENT_OPERATION = {"x-idempotency-required": True}
ETAG_OPERATION = {"x-etag-required": True}
ResultT = TypeVar("ResultT")
DistributionKeyT = TypeVar("DistributionKeyT")


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _canonical_subject_key(value: str) -> str:
    normalized = "".join(value.casefold().split())
    if len(normalized) < 3:
        raise ValueError("subject key must contain at least three non-whitespace characters")
    return normalized


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a UTC offset")
    return value


def _validate_probability_distribution(
    value: dict[DistributionKeyT, float],
) -> dict[DistributionKeyT, float]:
    if not value or any(probability < 0 for probability in value.values()):
        raise ValueError("probabilities must be non-negative")
    if abs(sum(value.values()) - 1.0) > 1e-9:
        raise ValueError("probabilities must sum to one")
    return value


def _execute_idempotent(
    *,
    service: MarketGovernanceService,
    identity: IdentityContext,
    idempotency_key: str,
    operation_id: str,
    fingerprint_values: tuple[object, ...],
    command: Callable[[], ResultT],
) -> ResultT:
    normalized = [
        value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for value in fingerprint_values
    ]
    fingerprint = hashlib.sha256(
        json.dumps(
            [operation_id, *normalized],
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return service.execute_idempotent(
        identity=identity,
        idempotency_key=idempotency_key,
        fingerprint=fingerprint,
        command=command,
    )


class CreateCompetitorRequest(RequestModel):
    legal_name: str = Field(min_length=1, max_length=300)
    canonical_subject_key: str = Field(min_length=3, max_length=200)
    aliases: tuple[str, ...] = Field(default_factory=tuple, max_length=100)

    @field_validator("canonical_subject_key")
    @classmethod
    def normalize_subject_key(cls, value: str) -> str:
        return _canonical_subject_key(value)

    @field_validator("aliases")
    @classmethod
    def aliases_are_nonempty_and_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(alias.strip() for alias in value)
        if any(not alias or len(alias) > 300 for alias in normalized):
            raise ValueError("aliases must contain 1 to 300 characters")
        if len({alias.casefold() for alias in normalized}) != len(normalized):
            raise ValueError("aliases must be unique")
        return normalized


class UpdateCompetitorDraftRequest(RequestModel):
    legal_name: str | None = Field(default=None, min_length=1, max_length=300)
    canonical_subject_key: str | None = Field(default=None, min_length=3, max_length=200)
    aliases: tuple[str, ...] | None = Field(default=None, max_length=100)

    @field_validator("canonical_subject_key")
    @classmethod
    def normalize_subject_key(cls, value: str | None) -> str | None:
        return _canonical_subject_key(value) if value is not None else None

    @model_validator(mode="after")
    def at_least_one_field_is_present(self) -> Self:
        if self.legal_name is None and self.canonical_subject_key is None and self.aliases is None:
            raise ValueError("at least one competitor field must be provided")
        if self.aliases is not None:
            CreateCompetitorRequest.aliases_are_nonempty_and_unique(self.aliases)
        return self


class ArchiveCompetitorRequest(RequestModel):
    reason: str = Field(min_length=1, max_length=1000)


class CreateCompetitorSourceRequest(RequestModel):
    source_uri: str = Field(min_length=1, max_length=1024)
    source_type: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=120)
    legal_basis_ref: str = Field(min_length=1, max_length=200)
    retention_expires_at: datetime
    data_classification: DataClassification
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("retention_expires_at")
    @classmethod
    def retention_is_timezone_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class ReviewCompetitorSourceRequest(RequestModel):
    resolved_competitor_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class QuarantineCompetitorSourceRequest(RequestModel):
    reason: str = Field(min_length=1, max_length=1000)


class BuildCompetitorProfileRequest(RequestModel):
    source_ids: tuple[UUID, ...] = Field(min_length=1, max_length=100)
    participation_assumptions: dict[str, float] = Field(default_factory=dict)
    bid_assumptions: dict[str, float] = Field(default_factory=dict)
    potential_response_states: tuple[str, ...] = ()
    subjective_variables: dict[str, float] = Field(default_factory=dict)
    validity_assumptions: tuple[str, ...] = ()
    coverage_notes: str = Field(min_length=1, max_length=2000)
    bias_notes: str = Field(min_length=1, max_length=2000)
    drift_notes: str = Field(min_length=1, max_length=2000)
    data_quality: str = Field(min_length=1, max_length=120)


class ActionRequest(RequestModel):
    reason_code: str = Field(default="MANUAL_ACTION", min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class CreateMarketPriorRequest(RequestModel):
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=120)
    legal_basis_ref: str = Field(min_length=1, max_length=200)
    valid_from: datetime
    expires_at: datetime
    distribution: dict[str, float]

    @field_validator("valid_from", "expires_at")
    @classmethod
    def validity_is_timezone_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @field_validator("distribution")
    @classmethod
    def distribution_is_valid(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_probability_distribution(value)

    @model_validator(mode="after")
    def validity_period_is_ordered(self) -> Self:
        if self.expires_at <= self.valid_from:
            raise ValueError("expires_at must be later than valid_from")
        return self


class CreateUnknownEntrantProfileRequest(RequestModel):
    excluded_subject_keys: frozenset[str]
    count_distribution: dict[int, float]
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=100)
    expires_at: datetime

    @field_validator("excluded_subject_keys")
    @classmethod
    def normalize_excluded_subjects(cls, value: frozenset[str]) -> frozenset[str]:
        return frozenset(_canonical_subject_key(item) for item in value)

    @field_validator("count_distribution")
    @classmethod
    def count_distribution_is_valid(cls, value: dict[int, float]) -> dict[int, float]:
        if any(count < 0 for count in value):
            raise ValueError("unknown entrant counts must be non-negative")
        return _validate_probability_distribution(value)

    @field_validator("expires_at")
    @classmethod
    def expiry_is_timezone_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class CreateSubjectDeduplicationRunRequest(RequestModel):
    subject_keys: tuple[str, ...] = Field(min_length=1, max_length=10000)


class CompetitorListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[Competitor, ...]


class CompetitorSourceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CompetitorSource, ...]


class CompetitorProfileListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[CompetitorProfile, ...]


class MarketPriorListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[MarketPriorVersion, ...]


class UnknownEntrantProfileListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    items: tuple[UnknownEntrantProfileVersion, ...]


def get_fr05_service(request: Request) -> MarketGovernanceService:
    services = getattr(request.app.state, "market_services", None)
    if services is None:
        raise BiaiceError("INTERNAL_ERROR", detail="Market services are not configured.")
    return services.fr05


def _set_etag(response: Response, item: Competitor) -> None:
    response.headers["ETag"] = compute_etag(item.model_dump(mode="json"))


read_identity = PermissionGuard(Permission.GOVERNANCE_READ)
write_identity = PermissionGuard(Permission.GOVERNANCE_WRITE)


@router.get(
    "/competitors",
    operation_id="list_competitors",
    response_model=CompetitorListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_competitors(
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorListResponse:
    return CompetitorListResponse(items=service.list_competitors(identity=identity))


@router.post(
    "/competitors",
    operation_id="create_competitor",
    response_model=Competitor,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_competitor(
    body: CreateCompetitorRequest,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> Competitor:
    item = new_competitor(
        identity=identity,
        legal_name=body.legal_name,
        canonical_subject_key=body.canonical_subject_key,
        aliases=body.aliases,
        now=service.clock.now(),
    )
    item = _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="create_competitor",
        fingerprint_values=(body,),
        command=lambda: service.add_competitor(
            identity=identity,
            item=item,
            request_id=request.state.request_id,
        ),
    )
    _set_etag(response, item)
    return item


@router.get(
    "/competitors/{competitor_id}",
    operation_id="get_competitor",
    response_model=Competitor,
    responses=PROBLEM_RESPONSES,
)
def get_competitor(
    competitor_id: UUID,
    response: Response,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> Competitor:
    item = service.get_competitor(identity=identity, competitor_id=competitor_id)
    _set_etag(response, item)
    return item


@router.patch(
    "/competitors/{competitor_id}",
    operation_id="update_competitor_draft",
    response_model=Competitor,
    responses=PROBLEM_RESPONSES,
    openapi_extra=ETAG_OPERATION,
)
def update_competitor_draft(
    competitor_id: UUID,
    body: UpdateCompetitorDraftRequest,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(write_identity),
    if_match: str = Depends(require_if_match),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> Competitor:
    item = service.update_competitor_draft(
        identity=identity,
        competitor_id=competitor_id,
        if_match=if_match,
        legal_name=body.legal_name,
        canonical_subject_key=body.canonical_subject_key,
        aliases=body.aliases,
        request_id=request.state.request_id,
    )
    _set_etag(response, item)
    return item


@router.post(
    "/competitors/{competitor_id}/archive",
    operation_id="archive_competitor",
    response_model=Competitor,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def archive_competitor(
    competitor_id: UUID,
    body: ArchiveCompetitorRequest,
    request: Request,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> Competitor:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="archive_competitor",
        fingerprint_values=(competitor_id, body),
        command=lambda: service.archive_competitor(
            identity=identity,
            competitor_id=competitor_id,
            reason=body.reason,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/competitors/{competitor_id}/sources",
    operation_id="list_competitor_sources",
    response_model=CompetitorSourceListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_competitor_sources(
    competitor_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorSourceListResponse:
    return CompetitorSourceListResponse(
        items=service.list_sources(identity=identity, competitor_id=competitor_id)
    )


@router.post(
    "/competitors/{competitor_id}/sources",
    operation_id="create_competitor_source",
    response_model=CompetitorSource,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_competitor_source(
    competitor_id: UUID,
    body: CreateCompetitorSourceRequest,
    request: Request,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorSource:
    now = service.clock.now()
    item = CompetitorSource(
        source_id=uuid4(),
        competitor_id=competitor_id,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        source_uri=body.source_uri,
        source_type=body.source_type,
        purpose=body.purpose,
        legal_basis_ref=body.legal_basis_ref,
        retention_expires_at=body.retention_expires_at,
        data_classification=body.data_classification,
        evidence_refs=body.evidence_refs,
        notes=body.notes,
        actor_id=identity.subject_id,
        created_at=now,
        updated_at=now,
    )
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="create_competitor_source",
        fingerprint_values=(competitor_id, body),
        command=lambda: service.add_source(
            identity=identity,
            item=item,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/competitor-sources/{competitor_source_id}",
    operation_id="get_competitor_source",
    response_model=CompetitorSource,
    responses=PROBLEM_RESPONSES,
)
def get_competitor_source(
    competitor_source_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorSource:
    return service.get_source(identity=identity, source_id=competitor_source_id)


@router.post(
    "/competitor-sources/{competitor_source_id}/review",
    operation_id="review_competitor_source",
    response_model=CompetitorSource,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def review_competitor_source(
    competitor_source_id: UUID,
    request: Request,
    body: ReviewCompetitorSourceRequest = Body(default=ReviewCompetitorSourceRequest()),
    identity: IdentityContext = Depends(read_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorSource:
    source = service.get_source(identity=identity, source_id=competitor_source_id)
    resolved_competitor_id = body.resolved_competitor_id or source.competitor_id
    if resolved_competitor_id is None:
        raise BiaiceError(
            "REQUEST_VALIDATION_FAILED",
            detail="A resolved competitor ID is required before source review.",
        )
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="review_competitor_source",
        fingerprint_values=(competitor_source_id, body),
        command=lambda: service.review_source(
            identity=identity,
            source_id=competitor_source_id,
            resolved_competitor_id=resolved_competitor_id,
            reviewed_at=service.clock.now(),
            request_id=request.state.request_id,
        ),
    )


@router.post(
    "/competitor-sources/{competitor_source_id}/quarantine",
    operation_id="quarantine_competitor_source",
    response_model=CompetitorSource,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def quarantine_competitor_source(
    competitor_source_id: UUID,
    body: QuarantineCompetitorSourceRequest,
    request: Request,
    identity: IdentityContext = Depends(read_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorSource:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="quarantine_competitor_source",
        fingerprint_values=(competitor_source_id, body),
        command=lambda: service.quarantine_source(
            identity=identity,
            source_id=competitor_source_id,
            reason=body.reason,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/competitors/{competitor_id}/profiles",
    operation_id="list_competitor_profiles",
    response_model=CompetitorProfileListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_competitor_profiles(
    competitor_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorProfileListResponse:
    return CompetitorProfileListResponse(
        items=service.list_profiles(identity=identity, competitor_id=competitor_id)
    )


@router.post(
    "/competitors/{competitor_id}/profiles/build",
    operation_id="build_competitor_profile",
    response_model=CompetitorProfile,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def build_competitor_profile(
    competitor_id: UUID,
    body: BuildCompetitorProfileRequest,
    request: Request,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorProfile:
    now = service.clock.now()
    item = CompetitorProfile(
        profile_id=uuid4(),
        competitor_id=competitor_id,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        source_ids=body.source_ids,
        participation_assumptions=body.participation_assumptions,
        bid_assumptions=body.bid_assumptions,
        potential_response_states=body.potential_response_states,
        subjective_variables=body.subjective_variables,
        validity_assumptions=body.validity_assumptions,
        coverage_notes=body.coverage_notes,
        bias_notes=body.bias_notes,
        drift_notes=body.drift_notes,
        data_quality=body.data_quality,
        actor_id=identity.subject_id,
        created_at=now,
        updated_at=now,
    )
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="build_competitor_profile",
        fingerprint_values=(competitor_id, body),
        command=lambda: service.add_profile(
            identity=identity,
            item=item,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/competitor-profiles/{competitor_profile_id}",
    operation_id="get_competitor_profile",
    response_model=CompetitorProfile,
    responses=PROBLEM_RESPONSES,
)
def get_competitor_profile(
    competitor_profile_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorProfile:
    return service.get_profile(identity=identity, profile_id=competitor_profile_id)


@router.post(
    "/competitor-profiles/{competitor_profile_id}/publish",
    operation_id="publish_competitor_profile",
    response_model=CompetitorProfile,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_competitor_profile(
    competitor_profile_id: UUID,
    request: Request,
    body: ActionRequest = Body(default=ActionRequest()),
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> CompetitorProfile:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="publish_competitor_profile",
        fingerprint_values=(competitor_profile_id, body),
        command=lambda: service.publish_profile(
            identity=identity,
            profile_id=competitor_profile_id,
            published_at=service.clock.now(),
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/decision-units/{unit_id}/market-priors",
    operation_id="list_market_priors",
    response_model=MarketPriorListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_market_priors(
    unit_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> MarketPriorListResponse:
    return MarketPriorListResponse(
        items=service.list_market_priors(identity=identity, decision_unit_id=unit_id)
    )


@router.post(
    "/decision-units/{unit_id}/market-priors",
    operation_id="create_market_prior",
    response_model=MarketPriorVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_market_prior(
    unit_id: UUID,
    body: CreateMarketPriorRequest,
    request: Request,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> MarketPriorVersion:
    now = service.clock.now()
    item = MarketPriorVersion(
        market_prior_id=uuid4(),
        decision_unit_id=unit_id,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        evidence_refs=body.evidence_refs,
        purpose=body.purpose,
        legal_basis_ref=body.legal_basis_ref,
        valid_from=body.valid_from,
        expires_at=body.expires_at,
        distribution=body.distribution,
        actor_id=identity.subject_id,
        created_at=now,
        updated_at=now,
    )
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="create_market_prior",
        fingerprint_values=(unit_id, body),
        command=lambda: service.add_market_prior(
            identity=identity,
            item=item,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/market-priors/{market_prior_id}",
    operation_id="get_market_prior",
    response_model=MarketPriorVersion,
    responses=PROBLEM_RESPONSES,
)
def get_market_prior(
    market_prior_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> MarketPriorVersion:
    return service.get_market_prior(identity=identity, market_prior_id=market_prior_id)


@router.post(
    "/market-priors/{market_prior_id}/review",
    operation_id="review_market_prior",
    response_model=MarketPriorVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def review_market_prior(
    market_prior_id: UUID,
    request: Request,
    body: ActionRequest = Body(default=ActionRequest()),
    identity: IdentityContext = Depends(read_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> MarketPriorVersion:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="review_market_prior",
        fingerprint_values=(market_prior_id, body),
        command=lambda: service.review_market_prior(
            identity=identity,
            market_prior_id=market_prior_id,
            request_id=request.state.request_id,
        ),
    )


@router.post(
    "/market-priors/{market_prior_id}/publish",
    operation_id="publish_market_prior",
    response_model=MarketPriorVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_market_prior(
    market_prior_id: UUID,
    request: Request,
    body: ActionRequest = Body(default=ActionRequest()),
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> MarketPriorVersion:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="publish_market_prior",
        fingerprint_values=(market_prior_id, body),
        command=lambda: service.publish_market_prior(
            identity=identity,
            market_prior_id=market_prior_id,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/decision-units/{unit_id}/unknown-entrant-profiles",
    operation_id="list_unknown_entrant_profiles",
    response_model=UnknownEntrantProfileListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_unknown_entrant_profiles(
    unit_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> UnknownEntrantProfileListResponse:
    return UnknownEntrantProfileListResponse(
        items=service.list_unknown_profiles(identity=identity, decision_unit_id=unit_id)
    )


@router.post(
    "/decision-units/{unit_id}/unknown-entrant-profiles",
    operation_id="create_unknown_entrant_profile",
    response_model=UnknownEntrantProfileVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_unknown_entrant_profile(
    unit_id: UUID,
    body: CreateUnknownEntrantProfileRequest,
    request: Request,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> UnknownEntrantProfileVersion:
    now = service.clock.now()
    item = UnknownEntrantProfileVersion(
        profile_id=uuid4(),
        decision_unit_id=unit_id,
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        excluded_subject_keys=body.excluded_subject_keys,
        count_distribution=body.count_distribution,
        evidence_refs=body.evidence_refs,
        expires_at=body.expires_at,
        actor_id=identity.subject_id,
        created_at=now,
        updated_at=now,
    )
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="create_unknown_entrant_profile",
        fingerprint_values=(unit_id, body),
        command=lambda: service.add_unknown_profile(
            identity=identity,
            item=item,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/unknown-entrant-profiles/{unknown_entrant_profile_id}",
    operation_id="get_unknown_entrant_profile",
    response_model=UnknownEntrantProfileVersion,
    responses=PROBLEM_RESPONSES,
)
def get_unknown_entrant_profile(
    unknown_entrant_profile_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> UnknownEntrantProfileVersion:
    return service.get_unknown_profile(
        identity=identity,
        profile_id=unknown_entrant_profile_id,
    )


@router.post(
    "/unknown-entrant-profiles/{unknown_entrant_profile_id}/publish",
    operation_id="publish_unknown_entrant_profile",
    response_model=UnknownEntrantProfileVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_unknown_entrant_profile(
    unknown_entrant_profile_id: UUID,
    request: Request,
    body: ActionRequest = Body(default=ActionRequest()),
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> UnknownEntrantProfileVersion:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="publish_unknown_entrant_profile",
        fingerprint_values=(unknown_entrant_profile_id, body),
        command=lambda: service.publish_unknown_profile(
            identity=identity,
            profile_id=unknown_entrant_profile_id,
            request_id=request.state.request_id,
        ),
    )


@router.post(
    "/decision-units/{unit_id}/subject-deduplication-runs",
    operation_id="create_subject_deduplication_run",
    response_model=SubjectDeduplicationRun,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_subject_deduplication_run(
    unit_id: UUID,
    body: CreateSubjectDeduplicationRunRequest,
    request: Request,
    identity: IdentityContext = Depends(write_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> SubjectDeduplicationRun:
    return _execute_idempotent(
        service=service,
        identity=identity,
        idempotency_key=idempotency_key,
        operation_id="create_subject_deduplication_run",
        fingerprint_values=(unit_id, body),
        command=lambda: service.create_subject_deduplication_run(
            identity=identity,
            decision_unit_id=unit_id,
            subject_keys=body.subject_keys,
            request_id=request.state.request_id,
        ),
    )


@router.get(
    "/subject-deduplication-runs/{run_id}",
    operation_id="get_subject_deduplication_run",
    response_model=SubjectDeduplicationRun,
    responses=PROBLEM_RESPONSES,
)
def get_subject_deduplication_run(
    run_id: UUID,
    identity: IdentityContext = Depends(read_identity),
    service: MarketGovernanceService = Depends(get_fr05_service),
) -> SubjectDeduplicationRun:
    return service.get_subject_deduplication_run(identity=identity, run_id=run_id)
