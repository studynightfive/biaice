from __future__ import annotations

from types import SimpleNamespace

import jwt
import pytest
from conftest import DOMAIN_A, TENANT_A, StaticAuthenticator
from fastapi.testclient import TestClient

from biaice.core.audit import UnavailableAuditWriter
from biaice.core.auth import OidcJwtAuthenticator, Role
from biaice.core.config import Settings
from biaice.core.errors import BiaiceError
from biaice.main import create_app


def _keycloak_claims(roles: list[str]) -> dict:
    return {
        "sub": "00000000-0000-4000-8000-000000000021",
        "preferred_username": "m2-projects",
        "iss": "http://biaice.local:8080/realms/biaice",
        "aud": ["biaice-api"],
        "iat": 1_786_656_000,
        "exp": 1_786_659_600,
        "tenant_id": "00000000-0000-4000-8000-000000000001",
        "data_domain_id": "00000000-0000-4000-8000-000000000002",
        "project_ids": ["00000000-0000-4000-8000-000000000101"],
        "decision_unit_ids": ["00000000-0000-4000-8000-000000000201"],
        "realm_access": {"roles": roles},
        "amr": ["pwd"],
    }


def _oidc_authenticator(monkeypatch, claims: dict) -> OidcJwtAuthenticator:
    authenticator = OidcJwtAuthenticator(
        issuer="http://biaice.local:8080/realms/biaice",
        audience="biaice-api",
        jwks_url="http://keycloak:8080/realms/biaice/protocol/openid-connect/certs",
    )
    authenticator.jwk_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=object())
    )
    monkeypatch.setattr(jwt, "decode", lambda *_args, **_kwargs: claims)
    return authenticator


def test_keycloak_scope_and_member_roles_map_to_identity(monkeypatch) -> None:
    identity = _oidc_authenticator(
        monkeypatch, _keycloak_claims(["PROJECT_MANAGER", "RULE_EDITOR"])
    ).authenticate("signed-token")
    assert identity.roles == frozenset({Role.PROJECT_MANAGER, Role.RULE_EDITOR})
    assert str(identity.scope.tenant_id) == "00000000-0000-4000-8000-000000000001"
    assert identity.scope.project_ids


def test_token_without_a_biaice_membership_role_is_rejected(monkeypatch) -> None:
    authenticator = _oidc_authenticator(
        monkeypatch, _keycloak_claims(["offline_access", "default-roles-biaice"])
    )
    with pytest.raises(BiaiceError) as error:
        authenticator.authenticate("signed-token")
    assert error.value.code == "PERMISSION_DENIED"


def test_health_probes_use_fixed_root_paths_and_disclose_no_business_data() -> None:
    app = create_app(settings=Settings(environment="test"))
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        assert live.status_code == 200
        assert ready.status_code == 200
        assert live.json()["mode"] == "SYNTHETIC_ONLY"
        assert client.get("/api/v1/health/live").status_code == 404


def test_unauthenticated_business_request_is_rfc7807() -> None:
    app = create_app(settings=Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "AUTH_REQUIRED"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_identity_scope_comes_from_server_and_spoof_headers_are_rejected(
    identity, auth_headers
) -> None:
    app = create_app(
        settings=Settings(environment="test"),
        authenticator=StaticAuthenticator(identity),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/me",
            headers={
                **auth_headers,
                "X-Tenant-ID": str(TENANT_A),
                "X-Data-Domain-ID": str(DOMAIN_A),
            },
        )
    assert response.status_code == 400
    assert response.json()["code"] == "SCOPE_OVERRIDE_FORBIDDEN"


def test_contract_only_route_requires_auth_idempotency_then_returns_explicit_501(
    identity, auth_headers
) -> None:
    app = create_app(
        settings=Settings(environment="test"),
        authenticator=StaticAuthenticator(identity),
    )
    with TestClient(app) as client:
        unauthenticated = client.post("/api/v1/projects", json={})
        missing_idempotency = client.post("/api/v1/projects", headers=auth_headers, json={})
        contract_only = client.post(
            "/api/v1/projects",
            headers={**auth_headers, "Idempotency-Key": "create-project-0001"},
            json={"payload": {}},
        )
    assert unauthenticated.status_code == 401
    assert missing_idempotency.status_code == 400
    assert missing_idempotency.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert contract_only.status_code == 501
    assert contract_only.json()["code"] == "NOT_IMPLEMENTED"
    assert "CONTRACT_ONLY" in contract_only.json()["detail"]


def test_byok_guard_rejects_before_malformed_secret_body_is_parsed(identity, auth_headers) -> None:
    app = create_app(
        settings=Settings(environment="test", deployment_profile="synthetic_http"),
        authenticator=StaticAuthenticator(identity),
    )
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/ai-provider-configurations/00000000-0000-4000-8000-000000000099/credential",
            headers={
                **auth_headers,
                "Idempotency-Key": "credential-write-0001",
                "Content-Type": "application/json",
            },
            content=b'{"api_key":"SHOULD_NEVER_APPEAR",',
        )
    assert response.status_code == 503
    assert response.json()["code"] == "BYOK_SECRET_GATE_REQUIRED"
    assert "SHOULD_NEVER_APPEAR" not in response.text


def test_internal_provider_egress_authorizer_is_hidden_and_always_fails_closed() -> None:
    app = create_app(settings=Settings(environment="test"))
    assert "/internal/provider-egress/authorize" not in app.openapi()["paths"]

    with TestClient(app) as client:
        responses = (
            client.post(
                "/internal/provider-egress/authorize",
                json={
                    "grant": "OPAQUE_GRANT_MUST_NOT_BE_ECHOED",
                    "target_host": "provider.invalid",
                    "target_port": 443,
                },
            ),
            client.post(
                "/internal/provider-egress/authorize",
                headers={"Content-Type": "application/json"},
                content=b'{"grant":"MALFORMED_GRANT_MUST_NOT_BE_ECHOED",',
            ),
        )

    for response in responses:
        assert response.status_code == 503
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["code"] == "EGRESS_AUTHORIZATION_UNAVAILABLE"
        assert "GRANT_MUST_NOT_BE_ECHOED" not in response.text


def test_audit_unavailable_blocks_sensitive_job_command(identity, auth_headers) -> None:
    app = create_app(
        settings=Settings(environment="test"),
        authenticator=StaticAuthenticator(identity),
        audit_writer=UnavailableAuditWriter(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/jobs/00000000-0000-4000-8000-000000000099/cancel",
            headers={**auth_headers, "Idempotency-Key": "cancel-job-000001"},
        )
    assert response.status_code == 503
    assert response.json()["code"] == "AUDIT_UNAVAILABLE"
