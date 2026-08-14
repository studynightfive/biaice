from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from biaice.core.auth import Authenticator, IdentityContext, Role, TenantScope

TENANT_A = UUID("00000000-0000-4000-8000-000000000001")
TENANT_B = UUID("00000000-0000-4000-8000-000000000002")
DOMAIN_A = UUID("00000000-0000-4000-8000-000000000011")
DOMAIN_B = UUID("00000000-0000-4000-8000-000000000012")
ACTOR_A = UUID("00000000-0000-4000-8000-000000000021")


class StaticAuthenticator(Authenticator):
    def __init__(self, identity: IdentityContext) -> None:
        self.identity = identity

    def authenticate(self, token: str) -> IdentityContext:
        assert token
        return self.identity


@pytest.fixture
def identity() -> IdentityContext:
    return IdentityContext(
        subject_id=ACTOR_A,
        username="member1",
        display_name="Member One",
        roles=frozenset({Role.BID_MANAGER}),
        scope=TenantScope(tenant_id=TENANT_A, data_domain_id=DOMAIN_A),
        mfa_verified=True,
        authenticated_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token-value"}
