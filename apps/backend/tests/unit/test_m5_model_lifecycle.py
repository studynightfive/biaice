from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec
from biaice.modules.model_governance.application.model_lifecycle import (
    ModelLifecycleService,
)
from biaice.modules.model_governance.application.repository import (
    ExternalModelReference,
    InMemoryModelLifecycleRepository,
)
from biaice.modules.model_governance.domain.models import (
    ApprovalState,
    DatasetSnapshotCreate,
    DeploymentState,
    EvaluationMetricDefinition,
    EvaluationProtocolCreate,
    FeatureDataType,
    FeatureDefinition,
    FeatureSchemaCreate,
    MetricDirection,
    ModelApprovalCreate,
    ModelApprovalDecision,
    ModelArtifactCreate,
    ModelDeploymentCreate,
    ModelDeploymentRollback,
    PublicationState,
)

TENANT = UUID("00000000-0000-4000-8000-000000000501")
DOMAIN = UUID("00000000-0000-4000-8000-000000000502")
AUTHOR = UUID("00000000-0000-4000-8000-000000000503")
CHECKER = UUID("00000000-0000-4000-8000-000000000504")
CATALOG_ID = UUID("00000000-0000-4000-8000-000000000505")
CONFIG_ID = UUID("00000000-0000-4000-8000-000000000506")
NOW = datetime(2026, 8, 17, 4, 0, tzinfo=timezone.utc)
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


class FixedClock:
    def now(self) -> datetime:
        return NOW


def identity(
    *,
    subject_id: UUID = AUTHOR,
    roles: frozenset[Role] = frozenset({Role.GOVERNANCE_ADMIN}),
    tenant_id: UUID = TENANT,
    mfa: bool = True,
) -> IdentityContext:
    return IdentityContext(
        subject_id=subject_id,
        username="model-governance-test",
        roles=roles,
        scope=TenantScope(tenant_id=tenant_id, data_domain_id=DOMAIN),
        mfa_verified=mfa,
        authenticated_at=NOW,
    )


def build_service() -> tuple[
    ModelLifecycleService,
    InMemoryModelLifecycleRepository,
    InMemoryAppendOnlyAuditSink,
]:
    repository = InMemoryModelLifecycleRepository()
    repository.register_external_model_reference(
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
    sink = InMemoryAppendOnlyAuditSink()
    audit = HashChainAuditWriter(sink, clock=FixedClock())
    return (
        ModelLifecycleService(
            repository=repository,
            clock=FixedClock(),
            audit_writer=audit,
            cursor_codec=CursorCodec(b"m5-model-lifecycle-test-cursor-key"),
        ),
        repository,
        sink,
    )


def seed_evidence(
    service: ModelLifecycleService,
    *,
    artifact_hash: str = HASH_A,
    key_suffix: str = "a",
):
    author = identity()
    dataset = service.create_dataset(
        identity=author,
        command=DatasetSnapshotCreate(
            name="time-isolated evaluation sample",
            purpose="MODEL_EVALUATION",
            source_asset_ids=(uuid4(),),
            row_count=25,
            content_hash=HASH_A,
        ),
        idempotency_key=f"dataset-create-{key_suffix}-0001",
        request_id="request-dataset-create",
    )
    dataset = service.publish_dataset(
        identity=author,
        dataset_id=dataset.dataset_id,
        idempotency_key=f"dataset-publish-{key_suffix}-001",
        request_id="request-dataset-publish",
    )
    schema = service.create_feature_schema(
        identity=author,
        command=FeatureSchemaCreate(
            name="evaluation features",
            features=(FeatureDefinition(name="score", data_type=FeatureDataType.FLOAT),),
            schema_hash=HASH_A,
        ),
        idempotency_key=f"schema-create-{key_suffix}-00001",
        request_id="request-schema-create",
    )
    schema = service.publish_feature_schema(
        identity=author,
        feature_schema_id=schema.feature_schema_id,
        idempotency_key=f"schema-publish-{key_suffix}-001",
        request_id="request-schema-publish",
    )
    artifact = service.create_model_artifact(
        identity=author,
        command=ModelArtifactCreate(
            name=f"external model reference {key_suffix}",
            feature_schema_id=schema.feature_schema_id,
            catalog_id=CATALOG_ID,
            catalog_hash=HASH_A,
            provider_id="approved-provider",
            provider_model_id="approved-model",
            adapter_version="adapter-v1",
            api_version="api-v1",
            code_or_image_digest=artifact_hash,
            prompt_template_id=uuid4(),
            prompt_template_hash=HASH_A,
            parameter_schema_hash=HASH_A,
            dependency_lock_hash=HASH_A,
            evaluation_evidence_hash=HASH_A,
            randomness_protocol="provider randomness is recorded and independently reviewed",
            numeric_protocol="float64 aggregation with the protocol tolerances",
        ),
        idempotency_key=f"artifact-create-{key_suffix}-0001",
        request_id="request-artifact-create",
    )
    artifact = service.publish_model_artifact(
        identity=author,
        model_artifact_id=artifact.model_artifact_id,
        idempotency_key=f"artifact-publish-{key_suffix}-001",
        request_id="request-artifact-publish",
    )
    protocol = service.create_evaluation_protocol(
        identity=author,
        command=EvaluationProtocolCreate(
            name="time-isolated protocol",
            dataset_id=dataset.dataset_id,
            metrics=(
                EvaluationMetricDefinition(
                    code="mae",
                    direction=MetricDirection.MINIMIZE,
                    threshold=0.1,
                ),
            ),
            absolute_tolerance=0.001,
            relative_tolerance=0.01,
            aggregation_protocol="cluster by decision unit before aggregation",
            cluster_unit="DECISION_UNIT",
        ),
        idempotency_key=f"protocol-create-{key_suffix}-001",
        request_id="request-protocol-create",
    )
    protocol = service.publish_evaluation_protocol(
        identity=author,
        evaluation_protocol_id=protocol.evaluation_protocol_id,
        idempotency_key=f"protocol-publish-{key_suffix}-01",
        request_id="request-protocol-publish",
    )
    return dataset, schema, artifact, protocol


def approve(
    service: ModelLifecycleService,
    *,
    artifact_id: UUID,
    protocol_id: UUID,
    key_suffix: str,
):
    approval = service.create_model_approval(
        identity=identity(),
        command=ModelApprovalCreate(
            model_artifact_id=artifact_id,
            evaluation_protocol_id=protocol_id,
            intended_purpose="BID_REVIEW_ASSISTANCE",
            evidence_hash=HASH_A,
        ),
        idempotency_key=f"approval-create-{key_suffix}-001",
        request_id="request-approval-create",
    )
    return service.decide_model_approval(
        identity=identity(
            subject_id=CHECKER,
            roles=frozenset({Role.APPROVER}),
        ),
        model_approval_id=approval.model_approval_id,
        command=ModelApprovalDecision(
            decision=ApprovalState.APPROVED,
            rationale="independent evidence review passed",
        ),
        idempotency_key=f"approval-decide-{key_suffix}-001",
        request_id="request-approval-decide",
    )


def test_create_dataset_is_idempotent_and_audited_once() -> None:
    service, _, sink = build_service()
    command = DatasetSnapshotCreate(
        name="evaluation sample",
        purpose="MODEL_EVALUATION",
        source_asset_ids=(uuid4(),),
        row_count=10,
        content_hash=HASH_A,
    )

    first = service.create_dataset(
        identity=identity(),
        command=command,
        idempotency_key="dataset-idempotency-key-001",
        request_id="request-one",
    )
    replay = service.create_dataset(
        identity=identity(),
        command=command,
        idempotency_key="dataset-idempotency-key-001",
        request_id="request-two",
    )

    assert replay.dataset_id == first.dataset_id
    assert len(sink.list_events(identity().scope)) == 1
    with pytest.raises(BiaiceError) as error:
        service.create_dataset(
            identity=identity(),
            command=command.model_copy(update={"row_count": 11}),
            idempotency_key="dataset-idempotency-key-001",
            request_id="request-three",
        )
    assert error.value.code == "IDEMPOTENCY_CONFLICT"


def test_cross_tenant_resources_are_hidden_and_roles_are_enforced() -> None:
    service, _, _ = build_service()
    item = service.create_dataset(
        identity=identity(),
        command=DatasetSnapshotCreate(
            name="evaluation sample",
            purpose="MODEL_EVALUATION",
            source_asset_ids=(uuid4(),),
            row_count=10,
            content_hash=HASH_A,
        ),
        idempotency_key="dataset-cross-scope-key-001",
        request_id="request-create",
    )

    with pytest.raises(BiaiceError) as hidden:
        service.get_dataset(
            identity=identity(tenant_id=uuid4()),
            dataset_id=item.dataset_id,
        )
    assert hidden.value.code == "RESOURCE_NOT_FOUND"

    with pytest.raises(BiaiceError) as forbidden:
        service.create_dataset(
            identity=identity(roles=frozenset({Role.BID_MANAGER})),
            command=DatasetSnapshotCreate(
                name="forbidden",
                purpose="MODEL_EVALUATION",
                source_asset_ids=(uuid4(),),
                row_count=1,
                content_hash=HASH_A,
            ),
            idempotency_key="dataset-role-check-key-0001",
            request_id="request-forbidden",
        )
    assert forbidden.value.code == "PERMISSION_DENIED"


def test_approval_requires_mfa_and_independent_checker() -> None:
    service, _, _ = build_service()
    _, _, artifact, protocol = seed_evidence(service)
    command = ModelApprovalCreate(
        model_artifact_id=artifact.model_artifact_id,
        evaluation_protocol_id=protocol.evaluation_protocol_id,
        intended_purpose="BID_REVIEW_ASSISTANCE",
        evidence_hash=HASH_A,
    )

    with pytest.raises(BiaiceError) as missing_mfa:
        service.create_model_approval(
            identity=identity(mfa=False),
            command=command,
            idempotency_key="approval-no-mfa-key-00001",
            request_id="request-no-mfa",
        )
    assert missing_mfa.value.code == "MFA_REQUIRED"

    approval = service.create_model_approval(
        identity=identity(),
        command=command,
        idempotency_key="approval-maker-key-000001",
        request_id="request-maker",
    )
    with pytest.raises(BiaiceError) as maker_checker:
        service.decide_model_approval(
            identity=identity(),
            model_approval_id=approval.model_approval_id,
            command=ModelApprovalDecision(
                decision=ApprovalState.APPROVED,
                rationale="same actor must be rejected",
            ),
            idempotency_key="approval-same-actor-key-01",
            request_id="request-same-actor",
        )
    assert maker_checker.value.code == "MAKER_CHECKER_REQUIRED"


def test_deployment_activation_and_rollback_restore_previous_version() -> None:
    service, _, _ = build_service()
    _, _, artifact_one, protocol_one = seed_evidence(service, key_suffix="one")
    approval_one = approve(
        service,
        artifact_id=artifact_one.model_artifact_id,
        protocol_id=protocol_one.evaluation_protocol_id,
        key_suffix="one",
    )
    deployer = identity(roles=frozenset({Role.TENANT_AI_ADMIN}))
    deployment_one = service.create_model_deployment(
        identity=deployer,
        command=ModelDeploymentCreate(
            model_artifact_id=artifact_one.model_artifact_id,
            model_approval_id=approval_one.model_approval_id,
            provider_configuration_id=CONFIG_ID,
            deployment_slot="bid-review-primary",
            intended_purpose="BID_REVIEW_ASSISTANCE",
        ),
        idempotency_key="deployment-create-one-0001",
        request_id="request-deployment-one",
    )
    deployment_one = service.activate_model_deployment(
        identity=deployer,
        model_deployment_id=deployment_one.model_deployment_id,
        idempotency_key="deployment-activate-one-01",
        request_id="request-activate-one",
    )
    assert deployment_one.state is DeploymentState.ACTIVE

    _, _, artifact_two, protocol_two = seed_evidence(
        service,
        artifact_hash=HASH_B,
        key_suffix="two",
    )
    approval_two = approve(
        service,
        artifact_id=artifact_two.model_artifact_id,
        protocol_id=protocol_two.evaluation_protocol_id,
        key_suffix="two",
    )
    deployment_two = service.create_model_deployment(
        identity=deployer,
        command=ModelDeploymentCreate(
            model_artifact_id=artifact_two.model_artifact_id,
            model_approval_id=approval_two.model_approval_id,
            provider_configuration_id=CONFIG_ID,
            deployment_slot="bid-review-primary",
            intended_purpose="BID_REVIEW_ASSISTANCE",
        ),
        idempotency_key="deployment-create-two-0001",
        request_id="request-deployment-two",
    )
    deployment_two = service.activate_model_deployment(
        identity=deployer,
        model_deployment_id=deployment_two.model_deployment_id,
        idempotency_key="deployment-activate-two-01",
        request_id="request-activate-two",
    )
    assert deployment_two.supersedes_deployment_id == deployment_one.model_deployment_id
    assert (
        service.get_model_deployment(
            identity=deployer,
            model_deployment_id=deployment_one.model_deployment_id,
        ).state
        is DeploymentState.SUPERSEDED
    )

    rolled_back = service.rollback_model_deployment(
        identity=deployer,
        model_deployment_id=deployment_two.model_deployment_id,
        command=ModelDeploymentRollback(
            reason="monitoring breach",
            evidence_hash=HASH_C,
        ),
        idempotency_key="deployment-rollback-two-001",
        request_id="request-rollback-two",
    )
    assert rolled_back.state is DeploymentState.ROLLED_BACK
    assert (
        service.get_model_deployment(
            identity=deployer,
            model_deployment_id=deployment_one.model_deployment_id,
        ).state
        is DeploymentState.ACTIVE
    )
    assert len(service.list_rollback_events(identity=deployer).items) == 1


def test_catalog_hash_change_blocks_published_artifact_use() -> None:
    service, repository, _ = build_service()
    _, _, artifact, protocol = seed_evidence(service)
    repository.register_external_model_reference(
        ExternalModelReference(
            tenant_id=TENANT,
            data_domain_id=DOMAIN,
            catalog_id=CATALOG_ID,
            catalog_hash=HASH_B,
            provider_id="approved-provider",
            provider_model_id="approved-model",
            provider_configuration_ids=frozenset({CONFIG_ID}),
        )
    )

    with pytest.raises(BiaiceError) as stale:
        service.create_model_approval(
            identity=identity(),
            command=ModelApprovalCreate(
                model_artifact_id=artifact.model_artifact_id,
                evaluation_protocol_id=protocol.evaluation_protocol_id,
                intended_purpose="BID_REVIEW_ASSISTANCE",
                evidence_hash=HASH_A,
            ),
            idempotency_key="approval-stale-catalog-key-1",
            request_id="request-stale-catalog",
        )
    assert stale.value.code == "GATE_NOT_CURRENT"
    assert artifact.state is PublicationState.PUBLISHED
