"""Install authenticated 501 routes from the P0 operation catalog."""

from __future__ import annotations

import inspect
import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path
from pydantic import BaseModel, ConfigDict, Field, field_validator

from biaice.api.operation_catalog import OPERATION_CATALOG, OperationSpec
from biaice.core.auth import IdentityContext, get_identity
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError, ProblemDetails
from biaice.core.http import require_if_match
from biaice.core.idempotency import require_idempotency_key

router = APIRouter()
PATH_PARAMETER = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")
SCOPE_KEYS = frozenset(
    {"tenant_id", "data_domain_id", "project_scope", "decision_unit_scope"}
)


def _reject_client_scope(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in SCOPE_KEYS:
                raise ValueError(f"client scope field is forbidden: {path}.{key}")
            _reject_client_scope(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_client_scope(nested, f"{path}[{index}]")


class ContractOnlyCommand(BaseModel):
    """Temporary M0 command envelope; owner field schemas are not yet frozen."""

    model_config = ConfigDict(extra="forbid")
    reason_code: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def no_client_scope_override(cls, value: dict[str, Any]) -> dict[str, Any]:
        _reject_client_scope(value)
        return value


class ContractOnlyResource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    contract_only: bool = True
    operation_id: str
    owner: str
    schema_status: str


def _annotation_for_path_parameter(name: str) -> type:
    if name == "part_number":
        return int
    if name in {"object_type"}:
        return str
    return UUID


def _make_endpoint(spec: OperationSpec):
    async def endpoint(**kwargs: Any) -> ContractOnlyResource:
        del kwargs
        raise BiaiceError(
            "NOT_IMPLEMENTED",
            detail=(
                f"{spec.operation_id} is CONTRACT_ONLY in M0; {spec.owner} must freeze its field-level "
                "Pydantic schema and implement the handler before this operation can be enabled."
            ),
        )

    endpoint.__name__ = f"contract_only_{spec.operation_id}"
    endpoint.__doc__ = spec.summary
    parameters: list[inspect.Parameter] = []
    for name in PATH_PARAMETER.findall(spec.path):
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=_annotation_for_path_parameter(name),
                default=Path(...),
            )
        )
    if spec.method in {"POST", "PUT", "PATCH"}:
        parameters.append(
            inspect.Parameter(
                "body",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=ContractOnlyCommand | None,
                default=Body(default=None),
            )
        )
    parameters.append(
        inspect.Parameter(
            "identity",
            inspect.Parameter.KEYWORD_ONLY,
            annotation=IdentityContext,
            default=Depends(get_identity),
        )
    )
    if spec.idempotency_required:
        parameters.append(
            inspect.Parameter(
                "idempotency_key",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=str,
                default=Depends(require_idempotency_key),
            )
        )
    if spec.etag_required:
        parameters.append(
            inspect.Parameter(
                "if_match",
                inspect.Parameter.KEYWORD_ONLY,
                annotation=str,
                default=Depends(require_if_match),
            )
        )
    endpoint.__signature__ = inspect.Signature(
        parameters, return_annotation=ContractOnlyResource
    )
    return endpoint


for operation in OPERATION_CATALOG:
    responses = dict(PROBLEM_RESPONSES)
    responses[501] = {
        "model": ProblemDetails,
        "description": "CONTRACT_ONLY: handler and owner-frozen field schema are not implemented",
    }
    router.add_api_route(
        operation.path,
        _make_endpoint(operation),
        methods=[operation.method],
        operation_id=operation.operation_id,
        response_model=ContractOnlyResource,
        responses=responses,
        summary=operation.summary,
        tags=[operation.fr, "contract-only"],
        openapi_extra={
            "x-contract-only": True,
            "x-owner": operation.owner,
            "x-fr": operation.fr,
            "x-required-permission": operation.permission,
            "x-idempotency-required": operation.idempotency_required,
            "x-etag-required": operation.etag_required,
            "x-schema-status": operation.schema_status,
        },
    )
