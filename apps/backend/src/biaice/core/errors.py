"""Stable RFC 7807 errors and the M0 error-code catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    status: int
    title: str
    recoverable: bool
    remediation: str


ERROR_CATALOG: dict[str, ErrorDefinition] = {
    "AUTH_REQUIRED": ErrorDefinition(401, "Authentication required", True, "Sign in and retry."),
    "AUTH_NOT_CONFIGURED": ErrorDefinition(
        503, "Authentication unavailable", True, "Configure the approved OIDC verifier."
    ),
    "TOKEN_INVALID": ErrorDefinition(401, "Invalid access token", True, "Sign in again."),
    "MFA_REQUIRED": ErrorDefinition(
        403, "Multi-factor authentication required", True, "Complete MFA and retry."
    ),
    "PERMISSION_DENIED": ErrorDefinition(
        403,
        "Permission denied",
        False,
        "Ask a tenant administrator for the required role.",
    ),
    "TENANT_SCOPE_VIOLATION": ErrorDefinition(
        404, "Resource not found", False, "Use a resource in the authenticated scope."
    ),
    "SCOPE_OVERRIDE_FORBIDDEN": ErrorDefinition(
        400,
        "Client scope override is forbidden",
        False,
        "Remove tenant/data-domain scope fields and headers.",
    ),
    "RESOURCE_NOT_FOUND": ErrorDefinition(
        404, "Resource not found", False, "Check the resource identifier."
    ),
    "REQUEST_VALIDATION_FAILED": ErrorDefinition(
        422, "Request validation failed", True, "Correct the listed fields."
    ),
    "IDEMPOTENCY_KEY_REQUIRED": ErrorDefinition(
        400, "Idempotency key required", True, "Send a unique Idempotency-Key header."
    ),
    "INVALID_IDEMPOTENCY_KEY": ErrorDefinition(
        400, "Invalid idempotency key", True, "Use 16-128 URL-safe ASCII characters."
    ),
    "IDEMPOTENCY_CONFLICT": ErrorDefinition(
        409,
        "Idempotency key conflict",
        False,
        "Use the same payload or a new idempotency key.",
    ),
    "IF_MATCH_REQUIRED": ErrorDefinition(
        428, "If-Match required", True, "Refresh the draft and send its current ETag."
    ),
    "ETAG_MISMATCH": ErrorDefinition(
        412, "ETag mismatch", True, "Refresh the draft before retrying."
    ),
    "INVALID_CURSOR": ErrorDefinition(
        400, "Invalid pagination cursor", True, "Restart pagination without the cursor."
    ),
    "CURSOR_SCOPE_MISMATCH": ErrorDefinition(
        400,
        "Pagination cursor scope mismatch",
        False,
        "Do not reuse cursors across scopes.",
    ),
    "JOB_NOT_FOUND": ErrorDefinition(404, "Job not found", False, "Check the job identifier."),
    "JOB_NOT_CANCELLABLE": ErrorDefinition(
        409, "Job cannot be cancelled", False, "Refresh the job state."
    ),
    "JOB_NOT_RETRYABLE": ErrorDefinition(
        409,
        "Job cannot be retried",
        False,
        "Resolve the terminal failure or create a new command.",
    ),
    "JOB_STORE_UNAVAILABLE": ErrorDefinition(
        503, "Job store unavailable", True, "Retry after PostgreSQL recovers."
    ),
    "AUDIT_UNAVAILABLE": ErrorDefinition(
        503,
        "Audit writer unavailable",
        True,
        "Retry after audit integrity is restored.",
    ),
    "AUDIT_INTEGRITY_FAILED": ErrorDefinition(
        503,
        "Audit integrity check failed",
        False,
        "Keep sensitive operations blocked and restore from the independent anchor.",
    ),
    "DATABASE_UNAVAILABLE": ErrorDefinition(
        503, "Database unavailable", True, "Retry after PostgreSQL recovers."
    ),
    "GATE_ASSESSMENT_NOT_FOUND": ErrorDefinition(
        404, "Gate assessment not found", False, "Run the approved machine assessment."
    ),
    "GATE_EVIDENCE_VERIFIER_UNAVAILABLE": ErrorDefinition(
        503, "Gate verifier unavailable", True, "Restore the machine evidence verifier."
    ),
    "EGRESS_AUTHORIZATION_UNAVAILABLE": ErrorDefinition(
        503,
        "Provider egress authorization unavailable",
        True,
        "Keep Provider egress disabled until the atomic single-use grant store is bound.",
    ),
    "GATE_NOT_CURRENT": ErrorDefinition(
        503, "Required gate is not current", True, "Refresh and pass all gate evidence."
    ),
    "REAL_DATA_MODE_REQUIRED": ErrorDefinition(
        503,
        "Real-data gate required",
        True,
        "Use synthetic data or pass REAL_DATA_MODE.",
    ),
    "BYOK_SECRET_GATE_REQUIRED": ErrorDefinition(
        503,
        "BYOK secret gate required",
        True,
        "Pass BYOK_SECRET_GATE before submitting a credential.",
    ),
    "WAIVER_PROHIBITED": ErrorDefinition(
        409, "Waiver prohibited", False, "Resolve the mandatory gate evidence."
    ),
    "MAKER_CHECKER_REQUIRED": ErrorDefinition(
        409,
        "Independent checker required",
        True,
        "Choose a checker different from the maker.",
    ),
    "RISK_ACCEPTANCE_INVALID_PERIOD": ErrorDefinition(
        422,
        "Risk acceptance period is invalid",
        False,
        "valid_until must be later than valid_from.",
    ),
    "RISK_ACCEPTANCE_EXPIRED": ErrorDefinition(
        410,
        "Risk acceptance has expired",
        False,
        "Create a new risk acceptance for the current period.",
    ),
    "RISK_ACCEPTANCE_ALREADY_REVOKED": ErrorDefinition(
        409,
        "Risk acceptance is already revoked",
        False,
        "Keep the append-only history; create a new acceptance if needed.",
    ),
    "GOVERNANCE_STORE_UNAVAILABLE": ErrorDefinition(
        503,
        "Governance store unavailable",
        True,
        "Retry after the governance repository recovers.",
    ),
    "DELETION_BLOCKED_BY_LEGAL_HOLD": ErrorDefinition(
        409,
        "Deletion blocked by legal hold",
        True,
        "Release the hold through dual control.",
    ),
    "DELETION_RECEIPTS_INCOMPLETE": ErrorDefinition(
        409,
        "Deletion receipts incomplete",
        True,
        "Retry or escalate missing required replicas.",
    ),
    "DELETION_RECEIPT_INVALID": ErrorDefinition(
        409,
        "Deletion receipt invalid",
        False,
        "Obtain a verified receipt from the registered adapter.",
    ),
    "RETENTION_EXPIRED": ErrorDefinition(
        410,
        "Retention period expired",
        False,
        "The object is no longer available for formal use.",
    ),
    "NOT_IMPLEMENTED": ErrorDefinition(
        501,
        "Operation not implemented",
        False,
        "Wait for the owning module implementation.",
    ),
    "INTERNAL_ERROR": ErrorDefinition(
        500,
        "Internal server error",
        True,
        "Retry with the request_id or contact an administrator.",
    ),
}


class FieldProblem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    message: str
    error_type: str | None = None


class ProblemDetails(BaseModel):
    """RFC 7807 plus stable product error metadata."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type_uri: str = Field(alias="type")
    title: str
    status: int
    detail: str
    instance: str | None = None
    code: str
    request_id: str
    errors: list[FieldProblem] = Field(default_factory=list)
    recoverable: bool = False
    remediation: str | None = None


class BiaiceError(Exception):
    def __init__(
        self,
        code: str,
        *,
        detail: str | None = None,
        status: int | None = None,
        errors: Sequence[FieldProblem] = (),
    ) -> None:
        definition = ERROR_CATALOG.get(code)
        if definition is None:
            raise ValueError(f"unknown stable error code: {code}")
        self.code = code
        self.status = status or definition.status
        self.title = definition.title
        self.detail = detail or definition.title
        self.errors = list(errors)
        self.recoverable = definition.recoverable
        self.remediation = definition.remediation
        super().__init__(self.detail)


def problem_response(request: Request, error: BiaiceError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unavailable")
    problem = ProblemDetails(
        type=f"https://biaice.local/problems/{error.code.lower().replace('_', '-')}",
        title=error.title,
        status=error.status,
        detail=error.detail,
        instance=request.url.path,
        code=error.code,
        request_id=request_id,
        errors=error.errors,
        recoverable=error.recoverable,
        remediation=error.remediation,
    )
    return JSONResponse(
        status_code=error.status,
        content=problem.model_dump(mode="json", by_alias=True),
        media_type="application/problem+json",
        headers={"X-Request-ID": request_id},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BiaiceError)
    async def handle_biaice_error(request: Request, error: BiaiceError) -> JSONResponse:
        return problem_response(request, error)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        fields = [
            FieldProblem(
                field=".".join(
                    str(part)
                    for part in item["loc"]
                    if part not in {"body", "query", "path", "header"}
                ),
                message=item["msg"],
                error_type=item["type"],
            )
            for item in error.errors()
        ]
        return problem_response(
            request,
            BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="One or more request fields are invalid.",
                errors=fields,
            ),
        )

    @app.exception_handler(400)
    async def handle_malformed_request(request: Request, error: Exception) -> JSONResponse:
        # Starlette rejects malformed JSON before FastAPI can raise a
        # RequestValidationError. Keep this framework-level path inside the
        # same RFC 7807 boundary and never echo parser details or body bytes.
        del error
        return problem_response(
            request,
            BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                status=400,
                detail="The request body is not valid JSON.",
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        import logging

        logging.getLogger("biaice.error").exception(
            "Unhandled request failure request_id=%s path=%s",
            getattr(request.state, "request_id", "unavailable"),
            request.url.path,
            exc_info=error,
        )
        return problem_response(
            request,
            BiaiceError(
                "INTERNAL_ERROR",
                detail="The request failed without exposing internal or sensitive data.",
            ),
        )


PROBLEM_RESPONSES: Mapping[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails},
    401: {"model": ProblemDetails},
    403: {"model": ProblemDetails},
    404: {"model": ProblemDetails},
    409: {"model": ProblemDetails},
    412: {"model": ProblemDetails},
    # Python 3.12 calls HTTP 422 "Unprocessable Entity" while Python 3.13+
    # follows RFC 9110's "Unprocessable Content" wording. Keep the code-first
    # OpenAPI snapshot deterministic across supported Python minor versions.
    422: {"model": ProblemDetails, "description": "Unprocessable Content"},
    428: {"model": ProblemDetails},
    503: {"model": ProblemDetails},
    501: {"model": ProblemDetails},
    500: {"model": ProblemDetails},
}
