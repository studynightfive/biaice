"""Member-2 authorization. Uses roles already frozen by member 1; does not extend core.Permission."""

from biaice.core.auth import CurrentIdentity, IdentityContext, Role
from biaice.core.errors import BiaiceError

READ_ROLES = frozenset(
    {
        Role.PROJECT_MANAGER,
        Role.RULE_EDITOR,
        Role.BID_MANAGER,
        Role.TENANT_ADMIN,
        Role.DOCUMENT_STEWARD,
        Role.LEGAL_PRIVACY,
        Role.AUDITOR,
        Role.APPROVER,
    }
)
WRITE_ROLES = frozenset(
    {
        Role.PROJECT_MANAGER,
        Role.RULE_EDITOR,
        Role.BID_MANAGER,
        Role.TENANT_ADMIN,
    }
)
PUBLISH_ROLES = frozenset(
    {
        Role.BID_MANAGER,
        Role.LEGAL_PRIVACY,
        Role.PROJECT_MANAGER,
        Role.RULE_EDITOR,
    }
)


class Fr01Guard:
    """Fail-closed FR-01 guard. SYSTEM_ADMIN has no project/rule access by default."""

    def __init__(self, *, write: bool = False, publish: bool = False, mfa: bool = False) -> None:
        self.write = write
        self.publish = publish
        self.mfa = mfa

    def __call__(self, identity: CurrentIdentity) -> IdentityContext:
        if self.mfa and not identity.mfa_verified:
            raise BiaiceError("MFA_REQUIRED")
        allowed = PUBLISH_ROLES if self.publish else WRITE_ROLES if self.write else READ_ROLES
        if not identity.roles & allowed:
            raise BiaiceError("PERMISSION_DENIED")
        return identity
