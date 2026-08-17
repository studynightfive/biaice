"""Provider catalog, tenant configuration and redacted invocation API."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from biaice.api.operation_catalog import OPERATION_CATALOG
from biaice.core.auth import IdentityContext, get_identity
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.http import require_if_match
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.model_governance.application.provider_management import (
    ProviderManagementService,
    configuration_etag,
)
from biaice.modules.model_governance.domain.provider_models import (
    AIProviderConfiguration,
    ProviderActionCommand,
    ProviderCatalogCreate,
    ProviderCatalogDecision,
    ProviderCatalogVersion,
    ProviderConfigurationCreate,
    ProviderConfigurationPage,
    ProviderConfigurationSuccessorCreate,
    ProviderConfigurationUpdate,
    ProviderConnectionTestResult,
    ProviderCredentialReceipt,
    ProviderCredentialWrite,
    ProviderDeletionAccepted,
    ProviderInvocationPage,
    ProviderInvocationRecord,
    PublishedProviderCatalog,
)

router = APIRouter(prefix="/api/v1", tags=["FR-13", "provider-management"])
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageCursor = Annotated[str | None, Query(min_length=1, max_length=4096)]

PROVIDER_MANAGEMENT_OPERATION_IDS = frozenset(
    {
        "list_ai_provider_catalog",
        "create_ai_provider_catalog_version",
        "get_ai_provider_catalog_version",
        "publish_ai_provider_catalog_version",
        "revoke_ai_provider_catalog_version",
        "list_ai_provider_configurations",
        "create_ai_provider_configuration",
        "get_ai_provider_configuration",
        "update_ai_provider_configuration",
        "create_ai_provider_configuration_successor",
        "set_ai_provider_credential",
        "revoke_ai_provider_credential",
        "test_ai_provider_connection",
        "activate_ai_provider_configuration",
        "suspend_ai_provider_configuration",
        "revoke_ai_provider_configuration",
        "list_provider_invocations",
        "get_provider_invocation",
    }
)
_SPECS = {item.operation_id: item for item in OPERATION_CATALOG}


def _extra(operation_id: str) -> dict[str, Any]:
    spec = _SPECS[operation_id]
    return {
        "x-contract-only": False,
        "x-owner": spec.owner,
        "x-fr": spec.fr,
        "x-required-permission": spec.permission,
        "x-idempotency-required": spec.idempotency_required,
        "x-etag-required": spec.etag_required,
        "x-schema-status": "FROZEN",
    }


def get_provider_service(request: Request) -> ProviderManagementService:
    service = getattr(request.app.state, "provider_management_service", None)
    if service is None:
        raise BiaiceError("INTERNAL_ERROR", detail="Provider management is not configured.")
    return service


def _set_etag(response: Response, item: AIProviderConfiguration) -> None:
    response.headers["ETag"] = configuration_etag(item)


@router.get(
    "/ai-provider-catalog",
    operation_id="list_ai_provider_catalog",
    response_model=PublishedProviderCatalog,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("list_ai_provider_catalog"),
)
def list_ai_provider_catalog(
    identity: IdentityContext = Depends(get_identity),
    service: ProviderManagementService = Depends(get_provider_service),
) -> PublishedProviderCatalog:
    return service.list_catalog(identity=identity)


@router.post(
    "/platform/ai-provider-catalog-versions",
    operation_id="create_ai_provider_catalog_version",
    response_model=ProviderCatalogVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("create_ai_provider_catalog_version"),
)
def create_ai_provider_catalog_version(
    body: ProviderCatalogCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderCatalogVersion:
    return service.create_catalog(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/platform/ai-provider-catalog-versions/{catalog_id}",
    operation_id="get_ai_provider_catalog_version",
    response_model=ProviderCatalogVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("get_ai_provider_catalog_version"),
)
def get_ai_provider_catalog_version(
    catalog_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderCatalogVersion:
    return service.get_catalog(identity=identity, catalog_id=catalog_id)


def _decide_catalog(
    *,
    catalog_id: UUID,
    action: str,
    body: ProviderCatalogDecision,
    request: Request,
    identity: IdentityContext,
    idempotency_key: str,
    service: ProviderManagementService,
) -> ProviderCatalogVersion:
    return service.decide_catalog(
        identity=identity,
        catalog_id=catalog_id,
        action=action,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/platform/ai-provider-catalog-versions/{catalog_id}/publish",
    operation_id="publish_ai_provider_catalog_version",
    response_model=ProviderCatalogVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("publish_ai_provider_catalog_version"),
)
def publish_ai_provider_catalog_version(
    catalog_id: UUID,
    body: ProviderCatalogDecision,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderCatalogVersion:
    return _decide_catalog(
        catalog_id=catalog_id,
        action="publish",
        body=body,
        request=request,
        identity=identity,
        idempotency_key=idempotency_key,
        service=service,
    )


@router.post(
    "/platform/ai-provider-catalog-versions/{catalog_id}/revoke",
    operation_id="revoke_ai_provider_catalog_version",
    response_model=ProviderCatalogVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("revoke_ai_provider_catalog_version"),
)
def revoke_ai_provider_catalog_version(
    catalog_id: UUID,
    body: ProviderCatalogDecision,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderCatalogVersion:
    return _decide_catalog(
        catalog_id=catalog_id,
        action="revoke",
        body=body,
        request=request,
        identity=identity,
        idempotency_key=idempotency_key,
        service=service,
    )


@router.get(
    "/ai-provider-configurations",
    operation_id="list_ai_provider_configurations",
    response_model=ProviderConfigurationPage,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("list_ai_provider_configurations"),
)
def list_ai_provider_configurations(
    limit: PageLimit = 100,
    cursor: PageCursor = None,
    identity: IdentityContext = Depends(get_identity),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderConfigurationPage:
    return service.list_configurations(identity=identity, limit=limit, cursor=cursor)


@router.post(
    "/ai-provider-configurations",
    operation_id="create_ai_provider_configuration",
    response_model=AIProviderConfiguration,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("create_ai_provider_configuration"),
)
def create_ai_provider_configuration(
    body: ProviderConfigurationCreate,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> AIProviderConfiguration:
    item = service.create_configuration(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    _set_etag(response, item)
    return item


@router.get(
    "/ai-provider-configurations/{config_id}",
    operation_id="get_ai_provider_configuration",
    response_model=AIProviderConfiguration,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("get_ai_provider_configuration"),
)
def get_ai_provider_configuration(
    config_id: UUID,
    response: Response,
    identity: IdentityContext = Depends(get_identity),
    service: ProviderManagementService = Depends(get_provider_service),
) -> AIProviderConfiguration:
    item = service.get_configuration(identity=identity, config_id=config_id)
    _set_etag(response, item)
    return item


@router.patch(
    "/ai-provider-configurations/{config_id}",
    operation_id="update_ai_provider_configuration",
    response_model=AIProviderConfiguration,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("update_ai_provider_configuration"),
)
def update_ai_provider_configuration(
    config_id: UUID,
    body: ProviderConfigurationUpdate,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(get_identity),
    if_match: str = Depends(require_if_match),
    service: ProviderManagementService = Depends(get_provider_service),
) -> AIProviderConfiguration:
    item = service.update_configuration(
        identity=identity,
        config_id=config_id,
        command=body,
        if_match=if_match,
        request_id=request.state.request_id,
    )
    _set_etag(response, item)
    return item


@router.post(
    "/ai-provider-configurations/{config_id}/successors",
    operation_id="create_ai_provider_configuration_successor",
    response_model=AIProviderConfiguration,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("create_ai_provider_configuration_successor"),
)
def create_ai_provider_configuration_successor(
    config_id: UUID,
    body: ProviderConfigurationSuccessorCreate,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> AIProviderConfiguration:
    item = service.create_successor(
        identity=identity,
        config_id=config_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    _set_etag(response, item)
    return item


@router.put(
    "/ai-provider-configurations/{config_id}/credential",
    operation_id="set_ai_provider_credential",
    response_model=ProviderCredentialReceipt,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("set_ai_provider_credential"),
)
def set_ai_provider_credential(
    config_id: UUID,
    body: ProviderCredentialWrite,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderCredentialReceipt:
    return service.set_credential(
        identity=identity,
        config_id=config_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.delete(
    "/ai-provider-configurations/{config_id}/credential",
    operation_id="revoke_ai_provider_credential",
    response_model=ProviderDeletionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("revoke_ai_provider_credential"),
)
def revoke_ai_provider_credential(
    config_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderDeletionAccepted:
    return service.revoke_credential(
        identity=identity,
        config_id=config_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/ai-provider-configurations/{config_id}/test-connection",
    operation_id="test_ai_provider_connection",
    response_model=ProviderConnectionTestResult,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("test_ai_provider_connection"),
)
def test_ai_provider_connection(
    config_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderConnectionTestResult:
    return service.test_connection(
        identity=identity,
        config_id=config_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/ai-provider-configurations/{config_id}/activate",
    operation_id="activate_ai_provider_configuration",
    response_model=AIProviderConfiguration,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("activate_ai_provider_configuration"),
)
def activate_ai_provider_configuration(
    config_id: UUID,
    body: ProviderActionCommand,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> AIProviderConfiguration:
    item = service.activate_configuration(
        identity=identity,
        config_id=config_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    _set_etag(response, item)
    return item


@router.post(
    "/ai-provider-configurations/{config_id}/suspend",
    operation_id="suspend_ai_provider_configuration",
    response_model=AIProviderConfiguration,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("suspend_ai_provider_configuration"),
)
def suspend_ai_provider_configuration(
    config_id: UUID,
    body: ProviderActionCommand,
    request: Request,
    response: Response,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> AIProviderConfiguration:
    item = service.suspend_configuration(
        identity=identity,
        config_id=config_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    _set_etag(response, item)
    return item


@router.post(
    "/ai-provider-configurations/{config_id}/revoke",
    operation_id="revoke_ai_provider_configuration",
    response_model=ProviderDeletionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("revoke_ai_provider_configuration"),
)
def revoke_ai_provider_configuration(
    config_id: UUID,
    body: ProviderActionCommand,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderDeletionAccepted:
    return service.revoke_configuration(
        identity=identity,
        config_id=config_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/provider-invocations",
    operation_id="list_provider_invocations",
    response_model=ProviderInvocationPage,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("list_provider_invocations"),
)
def list_provider_invocations(
    limit: PageLimit = 100,
    cursor: PageCursor = None,
    identity: IdentityContext = Depends(get_identity),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderInvocationPage:
    return service.list_invocations(identity=identity, limit=limit, cursor=cursor)


@router.get(
    "/provider-invocations/{invocation_id}",
    operation_id="get_provider_invocation",
    response_model=ProviderInvocationRecord,
    responses=PROBLEM_RESPONSES,
    openapi_extra=_extra("get_provider_invocation"),
)
def get_provider_invocation(
    invocation_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ProviderManagementService = Depends(get_provider_service),
) -> ProviderInvocationRecord:
    return service.get_invocation(identity=identity, invocation_id=invocation_id)
