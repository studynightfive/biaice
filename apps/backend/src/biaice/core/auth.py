"""OIDC identity, scope and server-side permission contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Protocol
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from biaice.core.errors import BiaiceError


class Role(StrEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    GOVERNANCE_ADMIN = "GOVERNANCE_ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    RULE_EDITOR = "RULE_EDITOR"
    DOCUMENT_STEWARD = "DOCUMENT_STEWARD"
    COMMERCIAL_ANALYST = "COMMERCIAL_ANALYST"
    TENANT_ADMIN = "TENANT_ADMIN"
    TENANT_AI_ADMIN = "TENANT_AI_ADMIN"
    PRIVACY_OFFICER = "PRIVACY_OFFICER"
    SIMULATION_ANALYST = "SIMULATION_ANALYST"
    REPORT_MANAGER = "REPORT_MANAGER"
    BID_MANAGER = "BID_MANAGER"
    DOCUMENT_SPECIALIST = "DOCUMENT_SPECIALIST"
    TECHNICAL_LEAD = "TECHNICAL_LEAD"
    FINANCE_AUTHOR = "FINANCE_AUTHOR"
    FINANCE_APPROVER = "FINANCE_APPROVER"
    LEGAL_PRIVACY = "LEGAL_PRIVACY"
    APPROVER = "APPROVER"
    AUDITOR = "AUDITOR"


class Permission(StrEnum):
    PROFILE_READ = "profile:read"
    JOB_READ = "job:read"
    JOB_COMMAND = "job:command"
    GATE_READ = "gate:read"
    GATE_ASSESS = "gate:assess"
    GATE_WAIVER_REQUEST = "gate:waiver:request"
    GATE_WAIVER_DECIDE = "gate:waiver:decide"
    MANUAL_OVERRIDE_APPEND = "manual-override:append"
    GOVERNANCE_READ = "governance:read"
    GOVERNANCE_WRITE = "governance:write"
    LEGAL_HOLD_MANAGE = "legal-hold:manage"
    LEGAL_HOLD_RELEASE = "legal-hold:release"
    DELETION_MANAGE = "deletion:manage"
    AUDIT_READ = "audit:read"
    AUDIT_INTEGRITY_RUN = "audit:integrity:run"
    SENSITIVE_CONTENT_READ = "sensitive-content:read"
    COST_READ = "cost:read"
    APPROVALS_RISK_READ = "fr-09b:read"
    APPROVALS_RISK_CREATE = "fr-09b:create"
    APPROVALS_RISK_REVOKE = "fr-09b:revoke"
    DOCUMENTS_READ = "fr-02:read"
    DOCUMENTS_CREATE = "fr-02:create"
    DOCUMENTS_PUT = "fr-02:put"
    DOCUMENTS_COMPLETE = "fr-02:complete"
    DOCUMENTS_CANCEL = "fr-02:cancel"
    DOCUMENTS_REVIEW = "fr-02:review"
    DOCUMENTS_RELEASE = "fr-02:release"
    DOCUMENTS_QUARANTINE = "fr-02:quarantine"
    DOCUMENTS_INHERIT = "fr-02:inherit"
    DOCUMENTS_OVERRIDE = "fr-02:override"
    DOCUMENTS_RESOLVE = "fr-02:resolve"
    DOCUMENTS_DETACH = "fr-02:detach"
    DOCUMENTS_RETRY = "fr-02:retry"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SYSTEM_ADMIN: frozenset(
        {Permission.PROFILE_READ, Permission.JOB_READ, Permission.GATE_READ}
    ),
    Role.GOVERNANCE_ADMIN: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GATE_READ,
            Permission.GOVERNANCE_READ,
            Permission.GOVERNANCE_WRITE,
            Permission.LEGAL_HOLD_MANAGE,
            Permission.DELETION_MANAGE,
            Permission.AUDIT_READ,
            Permission.AUDIT_INTEGRITY_RUN,
        }
    ),
    Role.PROJECT_MANAGER: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GATE_READ,
            Permission.GATE_WAIVER_REQUEST,
            Permission.GOVERNANCE_READ,
            Permission.DOCUMENTS_READ,
        }
    ),
    Role.RULE_EDITOR: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GOVERNANCE_READ,
        }
    ),
    Role.DOCUMENT_STEWARD: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GOVERNANCE_READ,
            Permission.DOCUMENTS_READ,
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_PUT,
            Permission.DOCUMENTS_COMPLETE,
            Permission.DOCUMENTS_CANCEL,
            Permission.DOCUMENTS_REVIEW,
            Permission.DOCUMENTS_RELEASE,
            Permission.DOCUMENTS_QUARANTINE,
            Permission.DOCUMENTS_INHERIT,
            Permission.DOCUMENTS_OVERRIDE,
            Permission.DOCUMENTS_RESOLVE,
            Permission.DOCUMENTS_DETACH,
            Permission.DOCUMENTS_RETRY,
        }
    ),
    Role.COMMERCIAL_ANALYST: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.COST_READ,
        }
    ),
    Role.TENANT_ADMIN: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GATE_READ,
            Permission.GATE_WAIVER_REQUEST,
            Permission.GOVERNANCE_READ,
        }
    ),
    Role.TENANT_AI_ADMIN: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GATE_READ,
        }
    ),
    Role.PRIVACY_OFFICER: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.GATE_READ,
            Permission.GATE_ASSESS,
            Permission.GATE_WAIVER_DECIDE,
            Permission.GOVERNANCE_READ,
            Permission.LEGAL_HOLD_RELEASE,
            Permission.AUDIT_READ,
            Permission.SENSITIVE_CONTENT_READ,
            Permission.DOCUMENTS_READ,
            Permission.DOCUMENTS_REVIEW,
            Permission.DOCUMENTS_RELEASE,
            Permission.DOCUMENTS_QUARANTINE,
            Permission.DOCUMENTS_RESOLVE,
        }
    ),
    Role.SIMULATION_ANALYST: frozenset(
        {Permission.PROFILE_READ, Permission.JOB_READ, Permission.JOB_COMMAND}
    ),
    Role.REPORT_MANAGER: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GATE_READ,
            Permission.APPROVALS_RISK_READ,
            Permission.APPROVALS_RISK_CREATE,
            Permission.APPROVALS_RISK_REVOKE,
        }
    ),
    Role.BID_MANAGER: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GATE_READ,
            Permission.GATE_WAIVER_REQUEST,
            Permission.GOVERNANCE_READ,
            Permission.APPROVALS_RISK_READ,
            Permission.APPROVALS_RISK_REVOKE,
            Permission.DOCUMENTS_READ,
        }
    ),
    Role.DOCUMENT_SPECIALIST: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GOVERNANCE_READ,
            Permission.DOCUMENTS_READ,
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_PUT,
            Permission.DOCUMENTS_COMPLETE,
            Permission.DOCUMENTS_CANCEL,
            Permission.DOCUMENTS_REVIEW,
            Permission.DOCUMENTS_INHERIT,
            Permission.DOCUMENTS_OVERRIDE,
            Permission.DOCUMENTS_DETACH,
            Permission.DOCUMENTS_RETRY,
        }
    ),
    Role.TECHNICAL_LEAD: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.JOB_COMMAND,
            Permission.GOVERNANCE_READ,
            Permission.DOCUMENTS_READ,
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_PUT,
            Permission.DOCUMENTS_COMPLETE,
            Permission.DOCUMENTS_CANCEL,
            Permission.DOCUMENTS_REVIEW,
            Permission.DOCUMENTS_INHERIT,
            Permission.DOCUMENTS_OVERRIDE,
            Permission.DOCUMENTS_DETACH,
            Permission.DOCUMENTS_RETRY,
        }
    ),
    Role.FINANCE_AUTHOR: frozenset(
        {Permission.PROFILE_READ, Permission.JOB_READ, Permission.COST_READ}
    ),
    Role.FINANCE_APPROVER: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.COST_READ,
            Permission.GATE_WAIVER_DECIDE,
        }
    ),
    Role.LEGAL_PRIVACY: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.GATE_READ,
            Permission.GATE_ASSESS,
            Permission.GATE_WAIVER_DECIDE,
            Permission.GOVERNANCE_READ,
            Permission.GOVERNANCE_WRITE,
            Permission.LEGAL_HOLD_MANAGE,
            Permission.LEGAL_HOLD_RELEASE,
            Permission.DELETION_MANAGE,
            Permission.AUDIT_READ,
            Permission.AUDIT_INTEGRITY_RUN,
            Permission.SENSITIVE_CONTENT_READ,
        }
    ),
    Role.APPROVER: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.JOB_READ,
            Permission.GATE_READ,
            Permission.APPROVALS_RISK_READ,
            Permission.APPROVALS_RISK_REVOKE,
        }
    ),
    Role.AUDITOR: frozenset(
        {
            Permission.PROFILE_READ,
            Permission.GATE_READ,
            Permission.GOVERNANCE_READ,
            Permission.AUDIT_READ,
        }
    ),
}


class TenantScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: UUID
    data_domain_id: UUID
    project_ids: frozenset[UUID] = Field(default_factory=frozenset)
    decision_unit_ids: frozenset[UUID] = Field(default_factory=frozenset)
    all_projects: bool = False
    all_decision_units: bool = False

    def assert_allows(
        self,
        *,
        tenant_id: UUID,
        data_domain_id: UUID,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
    ) -> None:
        # A scope mismatch deliberately looks like a missing resource.
        if tenant_id != self.tenant_id or data_domain_id != self.data_domain_id:
            raise BiaiceError("TENANT_SCOPE_VIOLATION")
        if (
            project_id is not None
            and not self.all_projects
            and project_id not in self.project_ids
        ):
            raise BiaiceError("TENANT_SCOPE_VIOLATION")
        if (
            decision_unit_id is not None
            and not self.all_decision_units
            and decision_unit_id not in self.decision_unit_ids
        ):
            raise BiaiceError("TENANT_SCOPE_VIOLATION")


class IdentityContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: UUID
    username: str
    display_name: str | None = None
    roles: frozenset[Role]
    scope: TenantScope
    mfa_verified: bool = False
    authenticated_at: datetime
    session_id: str | None = None

    @property
    def permissions(self) -> frozenset[Permission]:
        permissions: set[Permission] = set()
        for role in self.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, frozenset()))
        return frozenset(permissions)


class Authenticator(Protocol):
    def authenticate(self, token: str) -> IdentityContext: ...


class DenyAllAuthenticator:
    def authenticate(self, token: str) -> IdentityContext:
        del token
        raise BiaiceError("AUTH_NOT_CONFIGURED")


class OidcJwtAuthenticator:
    """Strict Keycloak JWT verifier; symmetric/user-selected algorithms are rejected."""

    def __init__(self, *, issuer: str, audience: str, jwks_url: str) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self.jwk_client = jwt.PyJWKClient(jwks_url)

    def authenticate(self, token: str) -> IdentityContext:
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
            realm_roles = claims.get("realm_access", {}).get("roles", [])
            roles = frozenset(
                Role(role) for role in realm_roles if role in Role._value2member_map_
            )
            if not roles:
                raise BiaiceError("PERMISSION_DENIED")
            amr = set(claims.get("amr", []))
            return IdentityContext(
                subject_id=UUID(claims["sub"]),
                username=claims.get("preferred_username", claims["sub"]),
                display_name=claims.get("name"),
                roles=roles,
                scope=TenantScope(
                    tenant_id=UUID(claims["tenant_id"]),
                    data_domain_id=UUID(claims["data_domain_id"]),
                    project_ids=frozenset(
                        UUID(value) for value in claims.get("project_ids", [])
                    ),
                    decision_unit_ids=frozenset(
                        UUID(value) for value in claims.get("decision_unit_ids", [])
                    ),
                    all_projects=claims.get("all_projects", False) is True,
                    all_decision_units=claims.get("all_decision_units", False) is True,
                ),
                mfa_verified=bool({"mfa", "otp", "webauthn"} & amr),
                authenticated_at=datetime.fromtimestamp(
                    int(claims["iat"]), tz=timezone.utc
                ),
                session_id=claims.get("sid"),
            )
        except BiaiceError:
            raise
        except Exception as exc:
            raise BiaiceError("TOKEN_INVALID") from exc


bearer_scheme = HTTPBearer(auto_error=False)


def get_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> IdentityContext:
    pre_authenticated = getattr(request.state, "pre_authenticated_identity", None)
    if isinstance(pre_authenticated, IdentityContext):
        return pre_authenticated
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise BiaiceError("AUTH_REQUIRED")
    authenticator: Authenticator = request.app.state.authenticator
    return authenticator.authenticate(credentials.credentials)


CurrentIdentity = Annotated[IdentityContext, Depends(get_identity)]


class PermissionGuard:
    def __init__(self, *required: Permission, mfa: bool = False) -> None:
        self.required = frozenset(required)
        self.mfa = mfa

    def __call__(self, identity: CurrentIdentity) -> IdentityContext:
        if self.mfa and not identity.mfa_verified:
            raise BiaiceError("MFA_REQUIRED")
        if not self.required.issubset(identity.permissions):
            raise BiaiceError("PERMISSION_DENIED")
        return identity
