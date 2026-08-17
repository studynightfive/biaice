"""FR-12 privacy and external-processing API for synthetic/contract profiles."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Request

from biaice.core.auth import IdentityContext, Role, get_identity
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.market.privacy.application.services import (
    MarketResourceService,
    get_market_resource_service,
)
from biaice.modules.market.privacy.domain.models import (
    MarketActionCommand,
    MarketResourceCommand,
    MarketResourcePage,
    MarketResourceRecord,
    MarketResourceStateFilter,
)

router = APIRouter()


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    path: str
    list_stem: str
    resource_type: str
    id_parameter: str


@dataclass(frozen=True, slots=True)
class ActionSpec:
    resource: ResourceSpec
    action: str

    @property
    def operation_id(self) -> str:
        return f"{self.action.replace('-', '_')}_{self.resource.resource_type}"


RESOURCE_SPECS = (
    ResourceSpec(
        "processing-records",
        "processing_records",
        "processing_record",
        "processing_record_id",
    ),
    ResourceSpec(
        "legal-basis-evidence",
        "legal_basis_evidence",
        "legal_basis_evidence",
        "legal_basis_evidence_id",
    ),
    ResourceSpec(
        "notice-consent-records",
        "notice_consent_records",
        "notice_consent_record",
        "notice_consent_record_id",
    ),
    ResourceSpec("pia-records", "pia_records", "pia_record", "pia_record_id"),
    ResourceSpec(
        "cross-border-assessments",
        "cross_border_assessments",
        "cross_border_assessment",
        "cross_border_assessment_id",
    ),
    ResourceSpec(
        "provider-policies",
        "provider_policies",
        "provider_policy",
        "provider_policy_id",
    ),
    ResourceSpec("dsr-policies", "dsr_policies", "dsr_policy", "dsr_policy_id"),
    ResourceSpec(
        "load-profiles", "load_profiles", "load_profile", "load_profile_id"
    ),
    ResourceSpec(
        "data-subject-requests",
        "data_subject_requests",
        "data_subject_request",
        "data_subject_request_id",
    ),
    ResourceSpec(
        "incident-policies",
        "incident_policies",
        "incident_policy",
        "incident_policy_id",
    ),
    ResourceSpec("incidents", "incidents", "incident", "incident_id"),
)

_BY_RESOURCE_TYPE = {spec.resource_type: spec for spec in RESOURCE_SPECS}
ACTION_SPECS = tuple(
    ActionSpec(_BY_RESOURCE_TYPE[resource_type], action)
    for resource_type, actions in (
        ("pia_record", ("approve", "revoke")),
        (
            "cross_border_assessment",
            ("approve", "mark-not-required", "revoke", "expire"),
        ),
        (
            "provider_policy",
            ("approve", "mark-not-required", "revoke", "expire"),
        ),
        ("dsr_policy", ("publish", "archive")),
        ("load_profile", ("freeze",)),
        (
            "data_subject_request",
            ("verify-identity", "transition", "complete"),
        ),
        ("incident_policy", ("approve",)),
        ("incident", ("transition", "close")),
    )
    for action in actions
)

FR12_IMPLEMENTED_OPERATION_IDS = frozenset(
    {
        *(
            operation_id
            for spec in RESOURCE_SPECS
            for operation_id in (
                f"list_{spec.list_stem}",
                f"create_{spec.resource_type}",
                f"get_{spec.resource_type}",
            )
        ),
        *(spec.operation_id for spec in ACTION_SPECS),
        "append_consent_withdrawal",
    }
)

READ_ROLES = frozenset(
    {
        Role.AUDITOR,
        Role.GOVERNANCE_ADMIN,
        Role.LEGAL_PRIVACY,
        Role.PRIVACY_OFFICER,
        Role.TENANT_ADMIN,
        Role.TENANT_AI_ADMIN,
    }
)
WRITE_ROLES = frozenset(
    {Role.GOVERNANCE_ADMIN, Role.LEGAL_PRIVACY, Role.PRIVACY_OFFICER}
)


def _authorize(
    identity: IdentityContext, *, write: bool, require_mfa: bool = False
) -> None:
    allowed = WRITE_ROLES if write else READ_ROLES
    if not identity.roles.intersection(allowed):
        raise BiaiceError("PERMISSION_DENIED")
    if require_mfa and not identity.mfa_verified:
        raise BiaiceError("MFA_REQUIRED")


def _problem_responses() -> dict:
    return {code: value for code, value in PROBLEM_RESPONSES.items() if code != 501}


def _openapi_extra(*, permission: str, idempotency: bool) -> dict[str, object]:
    return {
        "x-contract-only": False,
        "x-owner": "member-5",
        "x-fr": "FR-12",
        "x-required-permission": permission,
        "x-idempotency-required": idempotency,
        "x-etag-required": False,
        # The command envelope itself is frozen for M0 synthetic metadata.
        # This does not authorize real personal data or replace the unsigned
        # legal/business DTO decisions recorded in the delivery handoff.
        "x-schema-status": "FROZEN",
    }


def _list_endpoint(spec: ResourceSpec):
    async def endpoint(
        request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = Query(default=None, max_length=4096),
        state: MarketResourceStateFilter = Query(default=None),
        identity: IdentityContext = Depends(get_identity),
        service: MarketResourceService = Depends(get_market_resource_service),
    ) -> MarketResourcePage:
        del request
        _authorize(identity, write=False)
        return service.list(
            identity=identity,
            resource_type=spec.resource_type,
            limit=limit,
            cursor=cursor,
            state=state.value if state is not None and state != "null" else None,
        )

    endpoint.__name__ = f"list_{spec.list_stem}"
    return endpoint


def _create_endpoint(spec: ResourceSpec):
    operation_id = f"create_{spec.resource_type}"

    async def endpoint(
        request: Request,
        body: MarketResourceCommand = Body(...),
        identity: IdentityContext = Depends(get_identity),
        idempotency_key: str = Depends(require_idempotency_key),
        service: MarketResourceService = Depends(get_market_resource_service),
    ) -> MarketResourceRecord:
        _authorize(identity, write=True)
        return service.create(
            identity=identity,
            resource_type=spec.resource_type,
            payload=body.model_dump(mode="json", exclude_none=True, exclude_unset=True),
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )

    endpoint.__name__ = operation_id
    return endpoint


def _get_endpoint(spec: ResourceSpec):
    operation_id = f"get_{spec.resource_type}"

    async def endpoint(
        resource_id: UUID = Path(..., alias=spec.id_parameter),
        identity: IdentityContext = Depends(get_identity),
        service: MarketResourceService = Depends(get_market_resource_service),
    ) -> MarketResourceRecord:
        _authorize(identity, write=False)
        return service.get(
            identity=identity,
            resource_type=spec.resource_type,
            resource_id=resource_id,
        )

    endpoint.__name__ = operation_id
    return endpoint


def _action_endpoint(spec: ActionSpec):
    operation_id = spec.operation_id

    async def endpoint(
        request: Request,
        resource_id: UUID = Path(..., alias=spec.resource.id_parameter),
        body: MarketActionCommand | None = Body(default=None),
        identity: IdentityContext = Depends(get_identity),
        idempotency_key: str = Depends(require_idempotency_key),
        service: MarketResourceService = Depends(get_market_resource_service),
    ) -> MarketResourceRecord:
        _authorize(identity, write=True, require_mfa=True)
        return service.action(
            identity=identity,
            resource_type=spec.resource.resource_type,
            resource_id=resource_id,
            action=spec.action,
            command=body or MarketActionCommand(),
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )

    endpoint.__name__ = operation_id
    return endpoint


for _resource in RESOURCE_SPECS:
    router.add_api_route(
        f"/api/v1/{_resource.path}",
        _list_endpoint(_resource),
        methods=["GET"],
        operation_id=f"list_{_resource.list_stem}",
        response_model=MarketResourcePage,
        responses=_problem_responses(),
        tags=["FR-12", "privacy"],
        summary=f"List {_resource.list_stem.replace('_', ' ')}",
        openapi_extra=_openapi_extra(permission="fr-12:read", idempotency=False),
    )
    router.add_api_route(
        f"/api/v1/{_resource.path}",
        _create_endpoint(_resource),
        methods=["POST"],
        operation_id=f"create_{_resource.resource_type}",
        response_model=MarketResourceRecord,
        responses=_problem_responses(),
        tags=["FR-12", "privacy"],
        summary=f"Create {_resource.resource_type.replace('_', ' ')}",
        openapi_extra=_openapi_extra(permission="fr-12:create", idempotency=True),
    )
    router.add_api_route(
        f"/api/v1/{_resource.path}/{{{_resource.id_parameter}}}",
        _get_endpoint(_resource),
        methods=["GET"],
        operation_id=f"get_{_resource.resource_type}",
        response_model=MarketResourceRecord,
        responses=_problem_responses(),
        tags=["FR-12", "privacy"],
        summary=f"Get {_resource.resource_type.replace('_', ' ')}",
        openapi_extra=_openapi_extra(permission="fr-12:read", idempotency=False),
    )

for _action in ACTION_SPECS:
    router.add_api_route(
        f"/api/v1/{_action.resource.path}/{{{_action.resource.id_parameter}}}/{_action.action}",
        _action_endpoint(_action),
        methods=["POST"],
        operation_id=_action.operation_id,
        response_model=MarketResourceRecord,
        responses=_problem_responses(),
        tags=["FR-12", "privacy"],
        summary=(
            f"{_action.action.replace('-', ' ').title()} "
            f"{_action.resource.resource_type.replace('_', ' ')}"
        ),
        openapi_extra=_openapi_extra(
            permission=f"fr-12:{_action.action.split('-', 1)[0]}+mfa",
            idempotency=True,
        ),
    )


@router.post(
    "/api/v1/consent-withdrawals",
    operation_id="append_consent_withdrawal",
    response_model=MarketResourceRecord,
    responses=_problem_responses(),
    tags=["FR-12", "privacy"],
    summary="Append consent withdrawal event",
    openapi_extra=_openapi_extra(permission="fr-12:append", idempotency=True),
)
def append_consent_withdrawal(
    request: Request,
    body: MarketResourceCommand = Body(...),
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: MarketResourceService = Depends(get_market_resource_service),
) -> MarketResourceRecord:
    _authorize(identity, write=True)
    return service.create(
        identity=identity,
        resource_type="consent_withdrawal",
        payload=body.model_dump(mode="json", exclude_none=True, exclude_unset=True),
        operation_id="append_consent_withdrawal",
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
