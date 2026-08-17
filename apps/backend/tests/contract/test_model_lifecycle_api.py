from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from biaice.api.model_lifecycle import MODEL_LIFECYCLE_OPERATION_IDS
from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import Authenticator, IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.main import create_app
from biaice.modules.model_governance.application.repository import ExternalModelReference

TENANT = UUID("00000000-0000-4000-8000-000000000601")
OTHER_TENANT = UUID("00000000-0000-4000-8000-000000000602")
DOMAIN = UUID("00000000-0000-4000-8000-000000000603")
AUTHOR = UUID("00000000-0000-4000-8000-000000000604")
CHECKER = UUID("00000000-0000-4000-8000-000000000605")
CATALOG_ID = UUID("00000000-0000-4000-8000-000000000606")
CONFIG_ID = UUID("00000000-0000-4000-8000-000000000607")
NOW = datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64


def model_identity(
    *,
    subject_id: UUID = AUTHOR,
    tenant_id: UUID = TENANT,
    roles: frozenset[Role] = frozenset({Role.GOVERNANCE_ADMIN}),
    mfa: bool = True,
) -> IdentityContext:
    return IdentityContext(
        subject_id=subject_id,
        username="model-governance-api",
        roles=roles,
        scope=TenantScope(tenant_id=tenant_id, data_domain_id=DOMAIN),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


class SwitchableAuthenticator(Authenticator):
    def __init__(self, identity: IdentityContext) -> None:
        self.identity = identity

    def authenticate(self, token: str) -> IdentityContext:
        assert token
        return self.identity


def build_lifecycle_client() -> tuple[TestClient, SwitchableAuthenticator]:
    authenticator = SwitchableAuthenticator(model_identity())
    app = create_app(
        settings=Settings(environment="test"),
        authenticator=authenticator,
        audit_writer=HashChainAuditWriter(InMemoryAppendOnlyAuditSink()),
    )
    app.state.model_lifecycle_repository.register_external_model_reference(
        ExternalModelReference(
            tenant_id=TENANT,
            data_domain_id=DOMAIN,
            catalog_id=CATALOG_ID,
            catalog_hash=HASH_A,
            provider_id="approved-provider",
            provider_model_id="approved-model",
            provider_configuration_ids=frozenset({CONFIG_ID}),
        )
    )
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer model-lifecycle-test-token"
    return client, authenticator


@pytest.fixture
def lifecycle_client() -> tuple[TestClient, SwitchableAuthenticator]:
    return build_lifecycle_client()


def post(
    client: TestClient,
    path: str,
    *,
    key: str,
    body: dict[str, object] | None = None,
):
    return client.post(
        path,
        headers={"Idempotency-Key": key},
        json=body,
    )


def dataset_body(*, row_count: int = 25) -> dict[str, object]:
    return {
        "name": "time-isolated evaluation sample",
        "purpose": "MODEL_EVALUATION",
        "source_asset_ids": [str(uuid4())],
        "row_count": row_count,
        "content_hash": HASH_A,
    }


def feature_schema_body(*, nullable: object = False) -> dict[str, object]:
    return {
        "name": "evaluation features",
        "features": [
            {
                "name": "score",
                "data_type": "FLOAT",
                "nullable": nullable,
                "allowed_values": [],
            }
        ],
        "schema_hash": HASH_A,
    }


def artifact_body(feature_schema_id: str, *, digest: str = HASH_A) -> dict[str, object]:
    return {
        "name": "external model reference",
        "feature_schema_id": feature_schema_id,
        "catalog_id": str(CATALOG_ID),
        "catalog_hash": HASH_A,
        "provider_id": "approved-provider",
        "provider_model_id": "approved-model",
        "adapter_version": "adapter-v1",
        "api_version": "api-v1",
        "code_or_image_digest": digest,
        "prompt_template_id": str(uuid4()),
        "prompt_template_hash": HASH_A,
        "parameter_schema_hash": HASH_A,
        "dependency_lock_hash": HASH_A,
        "evaluation_evidence_hash": HASH_A,
        "randomness_protocol": "provider randomness is recorded and independently reviewed",
        "numeric_protocol": "float64 aggregation with protocol tolerances",
    }


def protocol_body(dataset_id: str) -> dict[str, object]:
    return {
        "name": "time-isolated protocol",
        "dataset_id": dataset_id,
        "metrics": [
            {
                "code": "mae",
                "direction": "MINIMIZE",
                "threshold": 0.1,
            }
        ],
        "absolute_tolerance": 0.001,
        "relative_tolerance": 0.01,
        "aggregation_protocol": "cluster by decision unit before aggregation",
        "cluster_unit": "DECISION_UNIT",
    }


def assert_ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def test_all_33_operations_use_typed_non_contract_routes() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    found: dict[str, dict[str, object]] = {}
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id in MODEL_LIFECYCLE_OPERATION_IDS:
                found[operation_id] = operation

    assert set(found) == set(MODEL_LIFECYCLE_OPERATION_IDS)
    assert len(found) == 33
    for operation in found.values():
        assert operation["x-contract-only"] is False
        assert "contract-only" not in operation.get("tags", [])
        success_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert "ContractOnlyResource" not in str(success_schema)

    write_operation_ids = {
        operation_id
        for operation_id in MODEL_LIFECYCLE_OPERATION_IDS
        if not operation_id.startswith(("list_", "get_"))
    }
    assert len(write_operation_ids) == 17
    for operation_id in write_operation_ids:
        operation = found[operation_id]
        assert operation["x-idempotency-required"] is True
        assert any(
            parameter.get("in") == "header" and parameter.get("name") == "Idempotency-Key"
            for parameter in operation["parameters"]
        )

    for operation_id in {
        "create_model_approval",
        "decide_model_approval",
        "create_model_deployment",
        "activate_model_deployment",
        "rollback_model_deployment",
    }:
        assert found[operation_id]["x-required-permission"].endswith("+mfa")

    artifact_schema = schema["components"]["schemas"]["ModelArtifactCreate"]
    assert artifact_schema["additionalProperties"] is False
    assert "model_weights" not in artifact_schema["properties"]
    assert "endpoint_url" not in artifact_schema["properties"]


def test_dataset_api_requires_idempotency_and_hides_cross_tenant_reads(
    lifecycle_client: tuple[TestClient, SwitchableAuthenticator],
) -> None:
    client, authenticator = lifecycle_client
    body = dataset_body()

    missing_key = client.post("/api/v1/datasets", json=body)
    assert missing_key.status_code == 400
    assert missing_key.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    created = assert_ok(
        post(
            client,
            "/api/v1/datasets",
            key="dataset-create-api-key-0001",
            body=body,
        )
    )
    replay = assert_ok(
        post(
            client,
            "/api/v1/datasets",
            key="dataset-create-api-key-0001",
            body=body,
        )
    )
    assert replay["dataset_id"] == created["dataset_id"]

    conflict = post(
        client,
        "/api/v1/datasets",
        key="dataset-create-api-key-0001",
        body={**body, "row_count": 26},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

    authenticator.identity = model_identity(tenant_id=OTHER_TENANT)
    hidden = client.get(f"/api/v1/datasets/{created['dataset_id']}")
    assert hidden.status_code == 404
    assert hidden.json()["code"] == "RESOURCE_NOT_FOUND"


def test_dataset_list_uses_scoped_signed_cursor(
    lifecycle_client: tuple[TestClient, SwitchableAuthenticator],
) -> None:
    client, authenticator = lifecycle_client
    created_ids = {
        assert_ok(
            post(
                client,
                "/api/v1/datasets",
                key=f"dataset-page-create-{index:04d}",
                body=dataset_body(row_count=index),
            )
        )["dataset_id"]
        for index in range(3)
    }

    first = assert_ok(client.get("/api/v1/datasets", params={"limit": 2}))
    assert len(first["items"]) == 2
    assert first["has_more"] is True
    assert first["next_cursor"]

    second = assert_ok(
        client.get(
            "/api/v1/datasets",
            params={"limit": 2, "cursor": first["next_cursor"]},
        )
    )
    assert second["has_more"] is False
    assert {item["dataset_id"] for item in first["items"] + second["items"]} == created_ids

    cursor = first["next_cursor"]
    replacement = "A" if cursor[-1] != "A" else "B"
    tampered = client.get(
        "/api/v1/datasets",
        params={"cursor": f"{cursor[:-1]}{replacement}"},
    )
    assert tampered.status_code == 400
    assert tampered.json()["code"] == "INVALID_CURSOR"

    authenticator.identity = model_identity(tenant_id=OTHER_TENANT)
    cross_tenant = client.get(
        "/api/v1/datasets",
        params={"cursor": cursor},
    )
    assert cross_tenant.status_code == 400
    assert cross_tenant.json()["code"] == "CURSOR_SCOPE_MISMATCH"


def test_model_artifact_rejects_model_weights(
    lifecycle_client: tuple[TestClient, SwitchableAuthenticator],
) -> None:
    client, _ = lifecycle_client
    body = artifact_body(str(uuid4()))
    body["model_weights"] = "forbidden"

    response = post(
        client,
        "/api/v1/model-artifacts",
        key="artifact-forbidden-field-001",
        body=body,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_FAILED"


def test_feature_schema_nullable_rejects_integer(
    lifecycle_client: tuple[TestClient, SwitchableAuthenticator],
) -> None:
    client, _ = lifecycle_client

    response = post(
        client,
        "/api/v1/feature-schemas",
        key="feature-schema-strict-bool-001",
        body=feature_schema_body(nullable=0),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_FAILED"


def test_all_33_endpoints_form_a_governed_lifecycle(
    lifecycle_client: tuple[TestClient, SwitchableAuthenticator],
) -> None:
    client, authenticator = lifecycle_client

    assert_ok(client.get("/api/v1/datasets"))
    dataset = assert_ok(
        post(client, "/api/v1/datasets", key="chain-dataset-create-0001", body=dataset_body())
    )
    assert_ok(client.get(f"/api/v1/datasets/{dataset['dataset_id']}"))
    dataset = assert_ok(
        post(
            client,
            f"/api/v1/datasets/{dataset['dataset_id']}/publish",
            key="chain-dataset-publish-001",
        )
    )
    assert dataset["state"] == "PUBLISHED"

    assert_ok(client.get("/api/v1/feature-schemas"))
    schema = assert_ok(
        post(
            client,
            "/api/v1/feature-schemas",
            key="chain-schema-create-00001",
            body=feature_schema_body(),
        )
    )
    assert_ok(client.get(f"/api/v1/feature-schemas/{schema['feature_schema_id']}"))
    schema = assert_ok(
        post(
            client,
            f"/api/v1/feature-schemas/{schema['feature_schema_id']}/publish",
            key="chain-schema-publish-001",
        )
    )

    assert_ok(client.get("/api/v1/model-artifacts"))
    artifact = assert_ok(
        post(
            client,
            "/api/v1/model-artifacts",
            key="chain-artifact-create-001",
            body=artifact_body(schema["feature_schema_id"]),
        )
    )
    assert_ok(client.get(f"/api/v1/model-artifacts/{artifact['model_artifact_id']}"))
    artifact = assert_ok(
        post(
            client,
            f"/api/v1/model-artifacts/{artifact['model_artifact_id']}/publish",
            key="chain-artifact-publish-01",
        )
    )

    assert_ok(client.get("/api/v1/evaluation-protocols"))
    protocol = assert_ok(
        post(
            client,
            "/api/v1/evaluation-protocols",
            key="chain-protocol-create-001",
            body=protocol_body(dataset["dataset_id"]),
        )
    )
    assert_ok(client.get(f"/api/v1/evaluation-protocols/{protocol['evaluation_protocol_id']}"))
    protocol = assert_ok(
        post(
            client,
            f"/api/v1/evaluation-protocols/{protocol['evaluation_protocol_id']}/publish",
            key="chain-protocol-publish-01",
        )
    )

    assert_ok(client.get("/api/v1/calibration-artifacts"))
    calibration = assert_ok(
        post(
            client,
            "/api/v1/calibration-artifacts",
            key="chain-calibration-create-01",
            body={
                "model_artifact_id": artifact["model_artifact_id"],
                "dataset_id": dataset["dataset_id"],
                "evaluation_protocol_id": protocol["evaluation_protocol_id"],
                "purpose": "REVIEW_OUTCOME_MODEL",
                "method": "isotonic calibration on held-out outcomes",
                "artifact_hash": HASH_A,
                "evaluation_evidence_hash": HASH_A,
            },
        )
    )
    assert_ok(client.get(f"/api/v1/calibration-artifacts/{calibration['calibration_artifact_id']}"))

    approval = assert_ok(
        post(
            client,
            "/api/v1/model-approvals",
            key="chain-approval-create-0001",
            body={
                "model_artifact_id": artifact["model_artifact_id"],
                "evaluation_protocol_id": protocol["evaluation_protocol_id"],
                "calibration_artifact_id": calibration["calibration_artifact_id"],
                "intended_purpose": "BID_REVIEW_ASSISTANCE",
                "evidence_hash": HASH_A,
            },
        )
    )
    authenticator.identity = model_identity(
        subject_id=CHECKER,
        roles=frozenset({Role.APPROVER}),
    )
    approval = assert_ok(
        post(
            client,
            f"/api/v1/model-approvals/{approval['model_approval_id']}/decide",
            key="chain-approval-decide-0001",
            body={
                "decision": "APPROVED",
                "rationale": "independent evidence review passed",
            },
        )
    )
    assert approval["state"] == "APPROVED"
    authenticator.identity = model_identity()

    deployment = assert_ok(
        post(
            client,
            "/api/v1/model-deployments",
            key="chain-deployment-create-001",
            body={
                "model_artifact_id": artifact["model_artifact_id"],
                "model_approval_id": approval["model_approval_id"],
                "provider_configuration_id": str(CONFIG_ID),
                "deployment_slot": "bid-review-primary",
                "intended_purpose": "BID_REVIEW_ASSISTANCE",
            },
        )
    )
    deployment = assert_ok(
        post(
            client,
            f"/api/v1/model-deployments/{deployment['model_deployment_id']}/activate",
            key="chain-deployment-activate-01",
        )
    )
    assert deployment["state"] == "ACTIVE"

    assert_ok(client.get("/api/v1/monitoring-snapshots"))
    monitoring = assert_ok(
        post(
            client,
            "/api/v1/monitoring-snapshots",
            key="chain-monitoring-create-001",
            body={
                "model_deployment_id": deployment["model_deployment_id"],
                "evaluation_protocol_id": protocol["evaluation_protocol_id"],
                "window_start": (NOW - timedelta(days=1)).isoformat(),
                "window_end": NOW.isoformat(),
                "sample_count": 20,
                "metric_values": {"mae": 0.05},
                "drift_status": "NO_DRIFT",
                "evidence_hash": HASH_A,
            },
        )
    )
    assert_ok(client.get(f"/api/v1/monitoring-snapshots/{monitoring['monitoring_snapshot_id']}"))

    assert_ok(client.get("/api/v1/model-incidents"))
    incident = assert_ok(
        post(
            client,
            "/api/v1/model-incidents",
            key="chain-incident-create-0001",
            body={
                "model_deployment_id": deployment["model_deployment_id"],
                "monitoring_snapshot_id": monitoring["monitoring_snapshot_id"],
                "severity": "HIGH",
                "summary": "synthetic monitoring breach exercise",
                "detected_at": NOW.isoformat(),
                "evidence_hash": HASH_A,
            },
        )
    )
    assert_ok(client.get(f"/api/v1/model-incidents/{incident['model_incident_id']}"))

    assert_ok(client.get("/api/v1/rollback-events"))
    rollback_event = assert_ok(
        post(
            client,
            "/api/v1/rollback-events",
            key="chain-rollback-event-create-1",
            body={
                "model_deployment_id": deployment["model_deployment_id"],
                "from_model_artifact_id": artifact["model_artifact_id"],
                "model_incident_id": incident["model_incident_id"],
                "reason": "record the rehearsed rollback trigger",
                "evidence_hash": HASH_A,
            },
        )
    )
    assert_ok(client.get(f"/api/v1/rollback-events/{rollback_event['rollback_event_id']}"))

    successor = assert_ok(
        post(
            client,
            "/api/v1/model-deployments",
            key="chain-deployment-successor-1",
            body={
                "model_artifact_id": artifact["model_artifact_id"],
                "model_approval_id": approval["model_approval_id"],
                "provider_configuration_id": str(CONFIG_ID),
                "deployment_slot": "bid-review-primary",
                "intended_purpose": "BID_REVIEW_ASSISTANCE",
            },
        )
    )
    successor = assert_ok(
        post(
            client,
            f"/api/v1/model-deployments/{successor['model_deployment_id']}/activate",
            key="chain-successor-activate-001",
        )
    )
    rolled_back = assert_ok(
        post(
            client,
            f"/api/v1/model-deployments/{successor['model_deployment_id']}/rollback",
            key="chain-successor-rollback-001",
            body={
                "reason": "restore the previously approved deployment",
                "evidence_hash": HASH_B,
            },
        )
    )
    assert rolled_back["state"] == "ROLLED_BACK"
