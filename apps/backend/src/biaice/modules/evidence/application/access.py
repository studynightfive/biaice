"""FR-03/04 role gates kept inside member-4 until member-1 registers permissions."""

from __future__ import annotations

from biaice.core.auth import CurrentIdentity, IdentityContext, Role
from biaice.core.errors import BiaiceError


class RoleGuard:
    def __init__(self, allowed: frozenset[Role], *, mfa: bool = False) -> None:
        self.allowed = allowed
        self.mfa = mfa

    def __call__(self, identity: CurrentIdentity) -> IdentityContext:
        if self.mfa and not identity.mfa_verified:
            raise BiaiceError("MFA_REQUIRED")
        if identity.roles.isdisjoint(self.allowed):
            raise BiaiceError("PERMISSION_DENIED")
        return identity


FR03_READ = frozenset(
    {
        Role.PROJECT_MANAGER,
        Role.DOCUMENT_STEWARD,
        Role.COMMERCIAL_ANALYST,
        Role.PRIVACY_OFFICER,
        Role.BID_MANAGER,
        Role.DOCUMENT_SPECIALIST,
        Role.TECHNICAL_LEAD,
        Role.APPROVER,
    }
)
FR03_CREATE = frozenset({Role.DOCUMENT_SPECIALIST, Role.TECHNICAL_LEAD})
FR03_UPDATE = FR03_CREATE
FR03_PUBLISH = FR03_CREATE
FR03_SUPERSEDE = FR03_CREATE
FR03_REVIEW = frozenset({Role.DOCUMENT_STEWARD})
FR03_REVOKE = FR03_REVIEW
FR03_SATISFY = frozenset(
    {Role.PRIVACY_OFFICER, Role.BID_MANAGER, Role.APPROVER}
)
FR03_WAIVE = FR03_SATISFY
FR03_FAIL = FR03_SATISFY
FR03_EXPIRE = FR03_SATISFY
FR04_READ = frozenset(
    {
        Role.PROJECT_MANAGER,
        Role.COMMERCIAL_ANALYST,
        Role.PRIVACY_OFFICER,
        Role.BID_MANAGER,
        Role.FINANCE_AUTHOR,
        Role.FINANCE_APPROVER,
    }
)
FR04_CREATE = frozenset({Role.COMMERCIAL_ANALYST, Role.FINANCE_AUTHOR})
FR04_APPROVE = frozenset({Role.FINANCE_APPROVER})
FR04_PUBLISH = FR04_APPROVE
