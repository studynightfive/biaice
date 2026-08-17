from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from biaice.api.provider_management import PROVIDER_MANAGEMENT_OPERATION_IDS
from biaice.core.auth import Authenticator, IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.core.errors import BiaiceError
from biaice.core.security.gates import (
    BYOK_REQUIRED_EVIDENCE,
    EvidenceStatus,
    GateEvidence,
    GateName,
    GateService,
    InMemoryGateEvidenceProvider,
    build_machine_assessment,
)
from biaice.core.security.restricted_ports import CredentialUsageScope, SecretReference
from biaice.main import create_app
from biaice.modules.model_governance.application.provider_management import (
    ProviderConnectionOutcome,
    ProviderDeletionJob,
    ProviderRuntimePort,
)
from biaice.modules.model_governance.domain.provider_models import (
    ProviderHealth,
    ProviderInvocationState,
)

TENANT_ID = UUID("00000000-0000-4000-8000-000000000701")
DOMAIN_ID = UUID("00000000-0000-4000-8000-000000000702")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000703")
SYSTEM_ID = UUID("00000000-0000-4000-8000-000000000704")
GOVERNANCE_ID = UUID("00000000-0000-4000-8000-000000000705")
PRIVACY_ID = UUID("00000000-0000-4000-8000-000000000706")
AI_ADMIN_ID = UUID("00000000-0000-4000-8000-000000000707")
OTHER_ADMIN_ID = UUID("00000000-0000-4000-8000-000000000708")
FAKE_KEY = "test-only-non-secret-fixture-0001"


def _identity(
    subject_id: UUID,
    role: Role,
    *,
    tenant_id: UUID = TENANT_ID,
) -> IdentityContext:
    return IdentityContext(
        subject_id=subject_id,
        username=f"test-{role.value.lower()}",
        roles=frozenset({role}),
        scope=TenantScope(
            tenant_id=tenant_id,
            data_domain_id=DOMAIN_ID,
            all_projects=True,
            all_decision_units=True,
        ),
        mfa_verified=True,
        authenticated_at=datetime.now(timezone.utc),
    )


class MappingAuthenticator(Authenticator):
    def __init__(self) -> None:
        self.identities = {
            "system": _identity(SYSTEM_ID, Role.SYSTEM_ADMIN),
            "governance": _identity(GOVERNANCE_ID, Role.GOVERNANCE_ADMIN),
            "privacy": _identity(PRIVACY_ID, Role.PRIVACY_OFFICER),
            "ai-admin": _identity(AI_ADMIN_ID, Role.TENANT_AI_ADMIN),
            "other-ai-admin": _identity(
                OTHER_ADMIN_ID,
                Role.TENANT_AI_ADMIN,
                tenant_id=OTHER_TENANT_ID,
            ),
        }

    def authenticate(self, token: str) -> IdentityContext:
        return self.identities[token]


class ReferenceOnlySecretStore:
    """Test adapter that retains references, never credential plaintext."""

    def __init__(self) -> None:
        self.write_count = 0

    def write(
        self,
        *,
        scope: TenantScope,
        provider_id: str,
        purpose: str,
        plaintext: SecretStr,
    ) -> SecretReference:
        del scope, provider_id, purpose
        self.write_count += 1
        value = plaintext.get_secret_value()
        return SecretReference(
            reference_id=uuid4(),
            credential_version=1,
            fingerprint=hashlib.sha256(value.encode()).hexdigest(),
            last_four=value[-4:],
            usage_scope=CredentialUsageScope.TEST_ONLY,
            created_at=datetime.now(timezone.utc),
        )

    def rotate(
        self,
        *,
        scope: TenantScope,
        old_reference: SecretReference,
        plaintext: SecretStr,
    ) -> SecretReference:
        reference = self.write(
            scope=scope,
            provider_id="rotation",
            purpose="rotation",
            plaintext=plaintext,
        )
        return reference.model_copy(
            update={"credential_version": old_reference.credential_version + 1}
        )

    def authorize_business(
        self, *, scope: TenantScope, reference: SecretReference
    ) -> SecretReference:
        del scope
        return reference.model_copy(
            update={"usage_scope": CredentialUsageScope.BUSINESS_AND_DELETION}
        )

    def restrict_to_deletion(
        self, *, scope: TenantScope, reference: SecretReference
    ) -> SecretReference:
        del scope
        return reference.model_copy(
            update={"usage_scope": CredentialUsageScope.DELETION_ONLY}
        )

    def destroy(self, *, scope: TenantScope, reference: SecretReference) -> None:
        del scope, reference


class SuccessfulProviderRuntime(ProviderRuntimePort):
    def catalog_is_synced(self, *, catalog_id: UUID, catalog_hash: str) -> bool:
        return bool(catalog_id and len(catalog_hash) == 64)

    def test_connection(
        self,
        *,
        scope: TenantScope,
        configuration,
        credential: SecretReference,
    ) -> ProviderConnectionOutcome:
        del scope, configuration, credential
        return ProviderConnectionOutcome(
            state=ProviderInvocationState.SUCCEEDED,
            reachable=True,
            authenticated=True,
            model_available=True,
            rate_limited=False,
            provider_health=ProviderHealth.HEALTHY,
            request_hash="a" * 64,
            response_hash="b" * 64,
        )

    def enqueue_deletion(
        self,
        *,
        scope: TenantScope,
        configuration,
        credential: SecretReference | None,
        reason_code: str,
        idempotency_key: str,
    ) -> ProviderDeletionJob:
        del scope, configuration, credential, reason_code, idempotency_key
        job_id = uuid4()
        return ProviderDeletionJob(job_id=job_id, status_url=f"/api/v1/jobs/{job_id}")


def _pass_byok_provider() -> InMemoryGateEvidenceProvider:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    evidence = tuple(
        GateEvidence(
            evidence_key=key,
            status=EvidenceStatus.PASS,
            checked_at=now,
            checker="provider-contract-test",
            evidence_hash=hashlib.sha256(key.encode()).hexdigest(),
            expires_at=expires_at,
        )
        for key in sorted(BYOK_REQUIRED_EVIDENCE)
    )
    assessment = build_machine_assessment(
        gate_name=GateName.BYOK_SECRET_GATE,
        evidence=evidence,
        responsible_party="provider-contract-test",
        assessed_at=now,
        expires_at=expires_at,
    )
    return InMemoryGateEvidenceProvider((assessment,))


def _headers(token: str, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _create_privacy_evidence(client: TestClient) -> dict[str, str]:
    created: dict[str, str] = {}
    resources = {
        "legal_basis_evidence_id": "legal-basis-evidence",
        "provider_policy_id": "provider-policies",
        "pia_record_id": "pia-records",
        "cross_border_assessment_id": "cross-border-assessments",
    }
    for index, (field, path) in enumerate(resources.items(), start=1):
        response = client.post(
            f"/api/v1/{path}",
            headers=_headers("governance", f"privacy-create-{index:04d}"),
            json={
                "subject_scope": "synthetic-provider-contract",
                "justification_ref": f"test://provider/{path}",
                "retention_days": 30,
            },
        )
        assert response.status_code == 200, response.text
        created[field] = response.json()["resource_id"]
    actions = (
        ("provider-policies", created["provider_policy_id"], "approve"),
        ("pia-records", created["pia_record_id"], "approve"),
        (
            "cross-border-assessments",
            created["cross_border_assessment_id"],
            "mark-not-required",
        ),
    )
    for index, (path, resource_id, action) in enumerate(actions, start=1):
        response = client.post(
            f"/api/v1/{path}/{resource_id}/{action}",
            headers=_headers("privacy", f"privacy-approve-{index:04d}"),
            json={"reason_code": "VERIFIED_SYNTHETIC_ONLY"},
        )
        assert response.status_code == 200, response.text
    return created


def test_provider_management_full_safe_flow_and_redaction() -> None:
    settings = Settings(
        environment="test",
        deployment_profile="secure_https",
        public_origin="https://testserver",
        byok_enabled=True,
        trust_gateway_forwarded_headers=False,
    )
    authenticator = MappingAuthenticator()
    secret_store = ReferenceOnlySecretStore()
    runtime = SuccessfulProviderRuntime()
    app = create_app(
        settings=settings,
        authenticator=authenticator,
        gate_evidence_provider=_pass_byok_provider(),
        secret_store=secret_store,
        provider_runtime=runtime,
    )

    with TestClient(app, base_url="https://testserver") as client:
        catalog_response = client.post(
            "/api/v1/platform/ai-provider-catalog-versions",
            headers=_headers("system", "provider-catalog-create-0001"),
            json={
                "reason_code": "INITIAL_APPROVED_CANDIDATE",
                "entries": [
                    {
                        "provider_id": "example-provider",
                        "provider_legal_name": "Example Provider Ltd.",
                        "provider_model_id": "example-model-v1",
                        "display_name": "Example Model V1",
                        "api_host": "api.example.com",
                        "adapter_id": "example-v1",
                        "capabilities": ["TEXT_GENERATION"],
                        "regions": ["CN"],
                        "allowed_purposes": ["SYNTHETIC_ASSISTANCE"],
                        "max_input_tokens": 4096,
                        "redaction_policy_summary": "Synthetic inputs only.",
                        "training_use": "DISABLED",
                        "retention_days": 30,
                    }
                ],
            },
        )
        assert catalog_response.status_code == 200, catalog_response.text
        catalog = catalog_response.json()
        publish_response = client.post(
            f"/api/v1/platform/ai-provider-catalog-versions/{catalog['catalog_id']}/publish",
            headers=_headers("privacy", "provider-catalog-publish-0001"),
            json={
                "reason_code": "INDEPENDENT_PRIVACY_APPROVAL",
                "approval_evidence_hash": "c" * 64,
            },
        )
        assert publish_response.status_code == 200, publish_response.text
        public_catalog = client.get(
            "/api/v1/ai-provider-catalog",
            headers=_headers("ai-admin"),
        )
        assert public_catalog.status_code == 200
        assert public_catalog.json()["items"][0]["provider_model_id"] == "example-model-v1"
        assert "api_host" not in public_catalog.json()["items"][0]
        assert "adapter_id" not in public_catalog.json()["items"][0]

        evidence = _create_privacy_evidence(client)
        create_response = client.post(
            "/api/v1/ai-provider-configurations",
            headers=_headers("ai-admin", "provider-config-create-0001"),
            json={
                "catalog_id": catalog["catalog_id"],
                "catalog_hash": catalog["catalog_hash"],
                "provider_id": "example-provider",
                "provider_model_id": "example-model-v1",
                "purpose": "SYNTHETIC_ASSISTANCE",
                "monthly_budget_minor": 1000,
                "currency": "CNY",
                "timeout_seconds": 30,
                "retention_days": 7,
                **evidence,
            },
        )
        assert create_response.status_code == 200, create_response.text
        config_id = create_response.json()["config_id"]
        assert create_response.headers["etag"].startswith('"')

        credential_headers = _headers("ai-admin", "provider-credential-set-0001")
        credential_response = client.put(
            f"/api/v1/ai-provider-configurations/{config_id}/credential",
            headers=credential_headers,
            json={"api_key": FAKE_KEY},
        )
        replay = client.put(
            f"/api/v1/ai-provider-configurations/{config_id}/credential",
            headers=credential_headers,
            json={"api_key": FAKE_KEY},
        )
        assert credential_response.status_code == replay.status_code == 200
        assert credential_response.json() == replay.json()
        assert secret_store.write_count == 1
        assert FAKE_KEY not in credential_response.text
        assert credential_response.json()["credential_state"] == "UNVERIFIED"
        assert credential_response.json()["credential_usage_scope"] == "TEST_ONLY"

        test_response = client.post(
            f"/api/v1/ai-provider-configurations/{config_id}/test-connection",
            headers=_headers("ai-admin", "provider-connection-test-0001"),
        )
        assert test_response.status_code == 200, test_response.text
        assert test_response.json()["authenticated"] is True

        activate_response = client.post(
            f"/api/v1/ai-provider-configurations/{config_id}/activate",
            headers=_headers("ai-admin", "provider-activate-0001"),
            json={"reason_code": "ALL_GOVERNANCE_EVIDENCE_CURRENT"},
        )
        assert activate_response.status_code == 200, activate_response.text
        assert activate_response.json()["activation_state"] == "ACTIVE"
        assert activate_response.json()["credential_usage_scope"] == "BUSINESS_AND_DELETION"
        serialized = activate_response.text.lower()
        assert FAKE_KEY not in activate_response.text
        assert '"api_key"' not in serialized
        assert '"secret"' not in serialized
        assert '"plaintext"' not in serialized

        invocation_page = client.get(
            "/api/v1/provider-invocations",
            headers=_headers("ai-admin"),
        )
        assert invocation_page.status_code == 200
        assert len(invocation_page.json()["items"]) == 1
        invocation_id = invocation_page.json()["items"][0]["invocation_id"]
        invocation = client.get(
            f"/api/v1/provider-invocations/{invocation_id}",
            headers=_headers("ai-admin"),
        )
        assert invocation.status_code == 200
        assert "request_hash" in invocation.json()
        assert "response_hash" in invocation.json()

        cross_tenant = client.get(
            f"/api/v1/ai-provider-configurations/{config_id}",
            headers=_headers("other-ai-admin"),
        )
        assert cross_tenant.status_code == 404

        planned = client.post(
            f"/api/v1/ai-provider-configurations/{config_id}/successors",
            headers=_headers("ai-admin", "provider-successor-planned-0001"),
            json={
                "rotation_mode": "PLANNED",
                "reason_code": "PLANNED_CREDENTIAL_ROTATION",
            },
        )
        assert planned.status_code == 200, planned.text
        successor_id = planned.json()["config_id"]
        successor_key = "test-only-non-secret-fixture-0002"
        assert client.put(
            f"/api/v1/ai-provider-configurations/{successor_id}/credential",
            headers=_headers("ai-admin", "provider-successor-credential-0001"),
            json={"api_key": successor_key},
        ).status_code == 200
        assert client.post(
            f"/api/v1/ai-provider-configurations/{successor_id}/test-connection",
            headers=_headers("ai-admin", "provider-successor-test-0001"),
        ).status_code == 200
        rotated = client.post(
            f"/api/v1/ai-provider-configurations/{successor_id}/activate",
            headers=_headers("ai-admin", "provider-successor-activate-0001"),
            json={"reason_code": "PLANNED_SUCCESSOR_VERIFIED"},
        )
        assert rotated.status_code == 200, rotated.text
        predecessor = client.get(
            f"/api/v1/ai-provider-configurations/{config_id}",
            headers=_headers("ai-admin"),
        )
        assert predecessor.json()["activation_state"] == "SUSPENDED"
        assert rotated.json()["activation_state"] == "ACTIVE"

        compromise = client.post(
            f"/api/v1/ai-provider-configurations/{successor_id}/successors",
            headers=_headers("ai-admin", "provider-successor-compromise-0001"),
            json={
                "rotation_mode": "COMPROMISE",
                "reason_code": "CREDENTIAL_COMPROMISE_REPORTED",
            },
        )
        assert compromise.status_code == 200, compromise.text
        compromised_predecessor = client.get(
            f"/api/v1/ai-provider-configurations/{successor_id}",
            headers=_headers("ai-admin"),
        )
        assert compromised_predecessor.json()["activation_state"] == "REVOKED"
        assert compromised_predecessor.json()["credential_state"] == "REVOKED"
        assert compromised_predecessor.json()["credential_usage_scope"] == "NONE"
        assert compromise.json()["activation_state"] == "INACTIVE"

        # Gate loss must not disable the emergency credential restriction/deletion path.
        app.state.gate_service = GateService(settings)
        revoke_response = client.delete(
            f"/api/v1/ai-provider-configurations/{config_id}/credential",
            headers=_headers("ai-admin", "provider-credential-revoke-0001"),
        )
        assert revoke_response.status_code == 202, revoke_response.text
        assert revoke_response.json()["credential_usage_scope"] == "DELETION_ONLY"


def test_provider_openapi_is_frozen_and_never_exposes_plaintext_fields() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    operations = {
        operation["operationId"]: operation
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict)
        and operation.get("operationId") in PROVIDER_MANAGEMENT_OPERATION_IDS
    }
    assert set(operations) == set(PROVIDER_MANAGEMENT_OPERATION_IDS)
    assert all(operation["x-contract-only"] is False for operation in operations.values())
    assert all(operation["x-schema-status"] == "FROZEN" for operation in operations.values())
    credential_schema = schema["components"]["schemas"]["ProviderCredentialWrite"]
    assert credential_schema["additionalProperties"] is False
    assert credential_schema["properties"]["api_key"]["writeOnly"] is True
    response_schemas = {
        name: value
        for name, value in schema["components"]["schemas"].items()
        if name.startswith(("AIProvider", "ProviderCredential", "ProviderInvocation"))
        and name != "ProviderCredentialWrite"
    }
    serialized = str(response_schemas).lower()
    assert "api_key" not in serialized
    assert "plaintext" not in serialized


def test_byok_startup_requires_both_secure_provider_ports() -> None:
    settings = Settings(
        environment="test",
        deployment_profile="secure_https",
        public_origin="https://testserver",
        byok_enabled=True,
    )
    common = {
        "settings": settings,
        "authenticator": MappingAuthenticator(),
        "gate_evidence_provider": _pass_byok_provider(),
    }
    missing_store = create_app(**common)
    with pytest.raises(BiaiceError) as store_error:
        with TestClient(missing_store, base_url="https://testserver"):
            pass
    assert store_error.value.code == "SECRET_STORE_UNAVAILABLE"

    missing_runtime = create_app(
        **common,
        secret_store=ReferenceOnlySecretStore(),
    )
    with pytest.raises(BiaiceError) as runtime_error:
        with TestClient(missing_runtime, base_url="https://testserver"):
            pass
    assert runtime_error.value.code == "EGRESS_AUTHORIZATION_UNAVAILABLE"
