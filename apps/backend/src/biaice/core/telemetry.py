"""Local-only, de-identified telemetry envelope and request context middleware."""

from __future__ import annotations

import re
from contextvars import ContextVar
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

request_id_context: ContextVar[str] = ContextVar("request_id", default="unavailable")
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
PROHIBITED_TELEMETRY_KEYS = frozenset(
    {
        "body",
        "content",
        "plaintext",
        "api_key",
        "secret",
        "prompt",
        "model_response",
        "personal_data",
        "cost",
        "cost_detail",
        "raw_prompt",
        "response_body",
        "request_body",
        "raw_content",
        "document_text",
        "personal_information",
        "credential_plaintext",
        "access_token",
        "refresh_token",
        "authorization_header",
    }
)


def _validate_attributes(value: Any, path: str = "attributes") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            canonical_key = (
                re.sub(r"(?<!^)(?=[A-Z])", "_", key).replace("-", "_").lower()
            )
            if canonical_key in PROHIBITED_TELEMETRY_KEYS:
                raise ValueError(
                    f"sensitive telemetry field is forbidden: {path}.{key}"
                )
            _validate_attributes(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_attributes(nested, f"{path}[{index}]")


class TelemetryEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    event_name: str
    occurred_at: datetime
    tenant_pseudonym: str | None = None
    decision_unit_pseudonym: str | None = None
    request_id: str
    attributes: dict[str, str | int | bool | float | None] = Field(default_factory=dict)

    @field_validator("attributes")
    @classmethod
    def reject_sensitive_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        _validate_attributes(value)
        return value


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        supplied = request.headers.get("X-Request-ID")
        request_id = (
            supplied
            if supplied and SAFE_REQUEST_ID.fullmatch(supplied)
            else str(uuid4())
        )
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_context.reset(token)
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


class ScopeOverrideMiddleware(BaseHTTPMiddleware):
    FORBIDDEN_HEADERS = frozenset(
        {"x-tenant-id", "x-data-domain-id", "x-project-scope", "x-unit-scope"}
    )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        from biaice.core.errors import BiaiceError, problem_response

        if self.FORBIDDEN_HEADERS.intersection(
            header.lower() for header in request.headers
        ):
            return problem_response(request, BiaiceError("SCOPE_OVERRIDE_FORBIDDEN"))
        return await call_next(request)


class BYOKPreBodyGuardMiddleware(BaseHTTPMiddleware):
    """Reject credential/test bodies before FastAPI reads or validates them."""

    GUARDED_SUFFIXES = ("/credential", "/test-connection", "/activate")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        from biaice.core.errors import BiaiceError, problem_response
        from biaice.core.security.gates import GateName

        path = request.url.path.rstrip("/")
        guarded = path.startswith(
            "/api/v1/ai-provider-configurations/"
        ) and path.endswith(self.GUARDED_SUFFIXES)
        if not guarded:
            return await call_next(request)
        settings = request.app.state.settings
        forwarded_scheme = (
            request.headers.get("x-forwarded-proto")
            if settings.trust_gateway_forwarded_headers
            else None
        )
        forwarded_host = (
            request.headers.get("x-forwarded-host")
            if settings.trust_gateway_forwarded_headers
            else None
        )
        scheme = forwarded_scheme or request.url.scheme
        host = forwarded_host or request.headers.get("host", "")
        expected = settings.public_origin.removeprefix("https://")
        if (
            settings.deployment_profile != "secure_https"
            or scheme != "https"
            or host != expected
        ):
            return problem_response(
                request,
                BiaiceError(
                    "BYOK_SECRET_GATE_REQUIRED",
                    detail="Credential and connection-test routes require the fixed trusted HTTPS origin.",
                ),
            )
        try:
            request.app.state.gate_service.require(GateName.BYOK_SECRET_GATE)
        except BiaiceError as error:
            return problem_response(request, error)
        if not request.app.state.audit_writer.available:
            return problem_response(request, BiaiceError("AUDIT_UNAVAILABLE"))
        return await call_next(request)
