"""FR-13 model-governance lifecycle services.

The repository is intentionally in-process for the current synthetic M0
runtime. Every formal command remains tenant scoped, audited, idempotent, and
fail-closed against externally supplied Provider catalog/configuration evidence.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar, cast
from uuid import UUID, uuid4

from pydantic import BaseModel

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext, Role
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec
from biaice.modules.model_governance.application.repository import (
    ExternalModelReference,
    InMemoryModelLifecycleRepository,
)
from biaice.modules.model_governance.domain.models import (
    ApprovalState,
    CalibrationArtifactCreate,
    CalibrationArtifactVersion,
    DatasetSnapshotCreate,
    DatasetSnapshotVersion,
    DeploymentState,
    EvaluationProtocolCreate,
    EvaluationProtocolVersion,
    FeatureSchemaCreate,
    FeatureSchemaVersion,
    IncidentState,
    ModelApprovalCreate,
    ModelApprovalDecision,
    ModelApprovalVersion,
    ModelArtifactCreate,
    ModelArtifactVersion,
    ModelDeploymentCreate,
    ModelDeploymentRollback,
    ModelDeploymentVersion,
    ModelIncidentCreate,
    ModelIncidentEvent,
    ModelMonitoringSnapshot,
    MonitoringSnapshotCreate,
    PublicationState,
    PublishableVersion,
    RollbackEvent,
    RollbackEventCreate,
    ScopedVersion,
)

ResourceT = TypeVar("ResourceT", bound=ScopedVersion)
PublishableT = TypeVar("PublishableT", bound=PublishableVersion)

DATASETS = "datasets"
FEATURE_SCHEMAS = "feature_schemas"
MODEL_ARTIFACTS = "model_artifacts"
EVALUATION_PROTOCOLS = "evaluation_protocols"
CALIBRATION_ARTIFACTS = "calibration_artifacts"
MONITORING_SNAPSHOTS = "monitoring_snapshots"
MODEL_INCIDENTS = "model_incidents"
ROLLBACK_EVENTS = "rollback_events"
MODEL_APPROVALS = "model_approvals"
MODEL_DEPLOYMENTS = "model_deployments"

READ_ROLES = (
    Role.GOVERNANCE_ADMIN,
    Role.TENANT_AI_ADMIN,
    Role.TECHNICAL_LEAD,
    Role.APPROVER,
    Role.AUDITOR,
)
AUTHOR_ROLES = (
    Role.GOVERNANCE_ADMIN,
    Role.TENANT_AI_ADMIN,
    Role.TECHNICAL_LEAD,
)
APPROVER_ROLES = (Role.GOVERNANCE_ADMIN, Role.APPROVER)
DEPLOYER_ROLES = (Role.GOVERNANCE_ADMIN, Role.TENANT_AI_ADMIN)


@dataclass(frozen=True, slots=True)
class ModelLifecyclePage(Generic[ResourceT]):
    items: tuple[ResourceT, ...]
    next_cursor: str | None
    has_more: bool


def _require_role(identity: IdentityContext, *allowed: Role, mfa: bool = False) -> None:
    if mfa and not identity.mfa_verified:
        raise BiaiceError("MFA_REQUIRED")
    if not identity.roles.intersection(allowed):
        raise BiaiceError("PERMISSION_DENIED")


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _canonical(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(nested) for nested in value]
    return value


def _fingerprint(*values: object) -> str:
    payload = json.dumps(
        _canonical(values),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ModelLifecycleService:
    """Single application writer for the requested 33 FR-13 operations."""

    def __init__(
        self,
        *,
        repository: InMemoryModelLifecycleRepository,
        clock: Clock,
        audit_writer: AuditWriter,
        cursor_codec: CursorCodec,
    ) -> None:
        self.repository = repository
        self.clock = clock
        self.audit_writer = audit_writer
        self.cursor_codec = cursor_codec

    def _execute(
        self,
        *,
        identity: IdentityContext,
        operation_id: str,
        idempotency_key: str,
        request_id: str,
        fingerprint_values: tuple[object, ...],
        expected_type: type[ResourceT],
        object_type: str,
        object_id: Callable[[ResourceT], UUID],
        outcome: Callable[[ResourceT], str],
        command: Callable[[], ResourceT],
    ) -> ResourceT:
        require_audit(self.audit_writer)

        def audited_command() -> ResourceT:
            item = command()
            self.audit_writer.write(
                identity=identity,
                action=f"model_governance.{operation_id}",
                object_type=object_type,
                object_id=object_id(item),
                request_id=request_id,
                reason_code=operation_id.upper(),
                outcome=outcome(item),
                object_version_id=item.version_id,
            )
            return item

        return self.repository.execute_idempotent(
            scope=identity.scope,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            request_fingerprint=_fingerprint(operation_id, *fingerprint_values),
            expected_type=expected_type,
            command=audited_command,
        )

    def _list(
        self,
        *,
        identity: IdentityContext,
        collection: str,
        expected_type: type[ResourceT],
        resource_id: Callable[[ResourceT], UUID],
        limit: int,
        cursor: str | None,
    ) -> ModelLifecyclePage[ResourceT]:
        _require_role(identity, *READ_ROLES)
        if not 1 <= limit <= 200:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="List limit must be between 1 and 200.",
            )
        items = tuple(
            sorted(
                self.repository.list(
                    scope=identity.scope,
                    collection=collection,
                    expected_type=expected_type,
                ),
                key=lambda item: (item.created_at, str(resource_id(item))),
            )
        )
        start = 0
        if cursor is not None:
            decoded = self.cursor_codec.decode(cursor, scope=identity.scope)
            try:
                marker = next(
                    index
                    for index, item in enumerate(items)
                    if item.created_at.isoformat() == decoded.sort_key
                    and str(resource_id(item)) == decoded.tie_breaker
                )
            except StopIteration as exc:
                raise BiaiceError("INVALID_CURSOR") from exc
            start = marker + 1
        page_items = items[start : start + limit]
        has_more = start + len(page_items) < len(items)
        next_cursor = None
        if has_more and page_items:
            tail = page_items[-1]
            next_cursor = self.cursor_codec.encode(
                scope=identity.scope,
                sort_key=tail.created_at.isoformat(),
                tie_breaker=str(resource_id(tail)),
            )
        return ModelLifecyclePage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _get(
        self,
        *,
        identity: IdentityContext,
        collection: str,
        resource_id: UUID,
        expected_type: type[ResourceT],
        label: str,
    ) -> ResourceT:
        _require_role(identity, *READ_ROLES)
        item = self.repository.get(
            scope=identity.scope,
            collection=collection,
            resource_id=resource_id,
            expected_type=expected_type,
        )
        if item is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"{label} {resource_id} was not found in the authenticated scope.",
            )
        return item

    def _publish(
        self,
        *,
        identity: IdentityContext,
        collection: str,
        resource_id: UUID,
        expected_type: type[PublishableT],
        label: str,
        operation_id: str,
        idempotency_key: str,
        request_id: str,
        validate: Callable[[PublishableT], None] | None = None,
    ) -> PublishableT:
        _require_role(identity, *AUTHOR_ROLES)

        def publish() -> PublishableT:
            item = self._get(
                identity=identity,
                collection=collection,
                resource_id=resource_id,
                expected_type=expected_type,
                label=label,
            )
            if item.state is not PublicationState.DRAFT:
                raise BiaiceError("GATE_NOT_CURRENT", detail=f"{label} is already published.")
            if validate is not None:
                validate(item)
            published = cast(
                PublishableT,
                item.model_copy(
                    update={
                        "version_id": uuid4(),
                        "state": PublicationState.PUBLISHED,
                        "published_at": self.clock.now(),
                        "published_by": identity.subject_id,
                    }
                ),
            )
            self.repository.upsert(
                collection=collection,
                resource_id=resource_id,
                item=published,
            )
            return published

        return self._execute(
            identity=identity,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(resource_id,),
            expected_type=expected_type,
            object_type=label.replace(" ", ""),
            object_id=lambda item: resource_id,
            outcome=lambda item: item.state.value,
            command=publish,
        )

    def create_dataset(
        self,
        *,
        identity: IdentityContext,
        command: DatasetSnapshotCreate,
        idempotency_key: str,
        request_id: str,
    ) -> DatasetSnapshotVersion:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> DatasetSnapshotVersion:
            dataset_id = uuid4()
            item = DatasetSnapshotVersion(
                dataset_id=dataset_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                state=PublicationState.DRAFT,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                **command.model_dump(),
            )
            self.repository.upsert(collection=DATASETS, resource_id=dataset_id, item=item)
            return item

        return self._execute(
            identity=identity,
            operation_id="create_dataset",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=DatasetSnapshotVersion,
            object_type="DatasetSnapshotVersion",
            object_id=lambda item: item.dataset_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def list_datasets(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[DatasetSnapshotVersion]:
        return self._list(
            identity=identity,
            collection=DATASETS,
            expected_type=DatasetSnapshotVersion,
            resource_id=lambda item: item.dataset_id,
            limit=limit,
            cursor=cursor,
        )

    def get_dataset(self, *, identity: IdentityContext, dataset_id: UUID) -> DatasetSnapshotVersion:
        return self._get(
            identity=identity,
            collection=DATASETS,
            resource_id=dataset_id,
            expected_type=DatasetSnapshotVersion,
            label="Dataset snapshot",
        )

    def publish_dataset(
        self,
        *,
        identity: IdentityContext,
        dataset_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> DatasetSnapshotVersion:
        return self._publish(
            identity=identity,
            collection=DATASETS,
            resource_id=dataset_id,
            expected_type=DatasetSnapshotVersion,
            label="Dataset snapshot",
            operation_id="publish_dataset",
            idempotency_key=idempotency_key,
            request_id=request_id,
        )

    def _require_published_dataset(
        self, *, identity: IdentityContext, dataset_id: UUID
    ) -> DatasetSnapshotVersion:
        item = self.get_dataset(identity=identity, dataset_id=dataset_id)
        if item.state is not PublicationState.PUBLISHED:
            raise BiaiceError("GATE_NOT_CURRENT", detail="Dataset snapshot is not published.")
        return item

    def create_feature_schema(
        self,
        *,
        identity: IdentityContext,
        command: FeatureSchemaCreate,
        idempotency_key: str,
        request_id: str,
    ) -> FeatureSchemaVersion:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> FeatureSchemaVersion:
            feature_schema_id = uuid4()
            item = FeatureSchemaVersion(
                feature_schema_id=feature_schema_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                state=PublicationState.DRAFT,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=FEATURE_SCHEMAS,
                resource_id=feature_schema_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_feature_schema",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=FeatureSchemaVersion,
            object_type="FeatureSchemaVersion",
            object_id=lambda item: item.feature_schema_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def list_feature_schemas(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[FeatureSchemaVersion]:
        return self._list(
            identity=identity,
            collection=FEATURE_SCHEMAS,
            expected_type=FeatureSchemaVersion,
            resource_id=lambda item: item.feature_schema_id,
            limit=limit,
            cursor=cursor,
        )

    def get_feature_schema(
        self, *, identity: IdentityContext, feature_schema_id: UUID
    ) -> FeatureSchemaVersion:
        return self._get(
            identity=identity,
            collection=FEATURE_SCHEMAS,
            resource_id=feature_schema_id,
            expected_type=FeatureSchemaVersion,
            label="Feature schema",
        )

    def publish_feature_schema(
        self,
        *,
        identity: IdentityContext,
        feature_schema_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> FeatureSchemaVersion:
        return self._publish(
            identity=identity,
            collection=FEATURE_SCHEMAS,
            resource_id=feature_schema_id,
            expected_type=FeatureSchemaVersion,
            label="Feature schema",
            operation_id="publish_feature_schema",
            idempotency_key=idempotency_key,
            request_id=request_id,
        )

    def _require_published_feature_schema(
        self, *, identity: IdentityContext, feature_schema_id: UUID
    ) -> FeatureSchemaVersion:
        item = self.get_feature_schema(
            identity=identity,
            feature_schema_id=feature_schema_id,
        )
        if item.state is not PublicationState.PUBLISHED:
            raise BiaiceError("GATE_NOT_CURRENT", detail="Feature schema is not published.")
        return item

    def _require_external_model_reference(
        self,
        *,
        identity: IdentityContext,
        catalog_id: UUID,
        catalog_hash: str,
        provider_id: str,
        provider_model_id: str,
        provider_configuration_id: UUID | None = None,
    ) -> ExternalModelReference:
        reference = self.repository.get_external_model_reference(
            scope=identity.scope,
            catalog_id=catalog_id,
            provider_id=provider_id,
            provider_model_id=provider_model_id,
        )
        if reference is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail="The external Provider/model reference is not present in the catalog gate.",
            )
        if not reference.current or reference.catalog_hash != catalog_hash:
            raise BiaiceError(
                "GATE_NOT_CURRENT",
                detail="The Provider catalog reference is stale or its hash has changed.",
            )
        if (
            provider_configuration_id is not None
            and provider_configuration_id not in reference.provider_configuration_ids
        ):
            raise BiaiceError(
                "GATE_NOT_CURRENT",
                detail="The Provider configuration is not approved for this external model.",
            )
        return reference

    def create_model_artifact(
        self,
        *,
        identity: IdentityContext,
        command: ModelArtifactCreate,
        idempotency_key: str,
        request_id: str,
    ) -> ModelArtifactVersion:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> ModelArtifactVersion:
            self._require_published_feature_schema(
                identity=identity,
                feature_schema_id=command.feature_schema_id,
            )
            self._require_external_model_reference(
                identity=identity,
                catalog_id=command.catalog_id,
                catalog_hash=command.catalog_hash,
                provider_id=command.provider_id,
                provider_model_id=command.provider_model_id,
            )
            model_artifact_id = uuid4()
            item = ModelArtifactVersion(
                model_artifact_id=model_artifact_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                state=PublicationState.DRAFT,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=MODEL_ARTIFACTS,
                resource_id=model_artifact_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_model_artifact",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=ModelArtifactVersion,
            object_type="ModelArtifactVersion",
            object_id=lambda item: item.model_artifact_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def list_model_artifacts(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[ModelArtifactVersion]:
        return self._list(
            identity=identity,
            collection=MODEL_ARTIFACTS,
            expected_type=ModelArtifactVersion,
            resource_id=lambda item: item.model_artifact_id,
            limit=limit,
            cursor=cursor,
        )

    def get_model_artifact(
        self, *, identity: IdentityContext, model_artifact_id: UUID
    ) -> ModelArtifactVersion:
        return self._get(
            identity=identity,
            collection=MODEL_ARTIFACTS,
            resource_id=model_artifact_id,
            expected_type=ModelArtifactVersion,
            label="Model artifact",
        )

    def _validate_model_artifact_reference(
        self, *, identity: IdentityContext, item: ModelArtifactVersion
    ) -> None:
        self._require_external_model_reference(
            identity=identity,
            catalog_id=item.catalog_id,
            catalog_hash=item.catalog_hash,
            provider_id=item.provider_id,
            provider_model_id=item.provider_model_id,
        )

    def publish_model_artifact(
        self,
        *,
        identity: IdentityContext,
        model_artifact_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> ModelArtifactVersion:
        return self._publish(
            identity=identity,
            collection=MODEL_ARTIFACTS,
            resource_id=model_artifact_id,
            expected_type=ModelArtifactVersion,
            label="Model artifact",
            operation_id="publish_model_artifact",
            idempotency_key=idempotency_key,
            request_id=request_id,
            validate=lambda item: self._validate_model_artifact_reference(
                identity=identity,
                item=item,
            ),
        )

    def _require_published_model_artifact(
        self, *, identity: IdentityContext, model_artifact_id: UUID
    ) -> ModelArtifactVersion:
        item = self.get_model_artifact(
            identity=identity,
            model_artifact_id=model_artifact_id,
        )
        if item.state is not PublicationState.PUBLISHED:
            raise BiaiceError("GATE_NOT_CURRENT", detail="Model artifact is not published.")
        self._validate_model_artifact_reference(identity=identity, item=item)
        return item

    def create_evaluation_protocol(
        self,
        *,
        identity: IdentityContext,
        command: EvaluationProtocolCreate,
        idempotency_key: str,
        request_id: str,
    ) -> EvaluationProtocolVersion:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> EvaluationProtocolVersion:
            self._require_published_dataset(identity=identity, dataset_id=command.dataset_id)
            evaluation_protocol_id = uuid4()
            item = EvaluationProtocolVersion(
                evaluation_protocol_id=evaluation_protocol_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                state=PublicationState.DRAFT,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=EVALUATION_PROTOCOLS,
                resource_id=evaluation_protocol_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_evaluation_protocol",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=EvaluationProtocolVersion,
            object_type="EvaluationProtocolVersion",
            object_id=lambda item: item.evaluation_protocol_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def list_evaluation_protocols(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[EvaluationProtocolVersion]:
        return self._list(
            identity=identity,
            collection=EVALUATION_PROTOCOLS,
            expected_type=EvaluationProtocolVersion,
            resource_id=lambda item: item.evaluation_protocol_id,
            limit=limit,
            cursor=cursor,
        )

    def get_evaluation_protocol(
        self, *, identity: IdentityContext, evaluation_protocol_id: UUID
    ) -> EvaluationProtocolVersion:
        return self._get(
            identity=identity,
            collection=EVALUATION_PROTOCOLS,
            resource_id=evaluation_protocol_id,
            expected_type=EvaluationProtocolVersion,
            label="Evaluation protocol",
        )

    def publish_evaluation_protocol(
        self,
        *,
        identity: IdentityContext,
        evaluation_protocol_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> EvaluationProtocolVersion:
        return self._publish(
            identity=identity,
            collection=EVALUATION_PROTOCOLS,
            resource_id=evaluation_protocol_id,
            expected_type=EvaluationProtocolVersion,
            label="Evaluation protocol",
            operation_id="publish_evaluation_protocol",
            idempotency_key=idempotency_key,
            request_id=request_id,
            validate=lambda item: self._require_published_dataset(
                identity=identity,
                dataset_id=item.dataset_id,
            ),
        )

    def _require_published_protocol(
        self, *, identity: IdentityContext, evaluation_protocol_id: UUID
    ) -> EvaluationProtocolVersion:
        item = self.get_evaluation_protocol(
            identity=identity,
            evaluation_protocol_id=evaluation_protocol_id,
        )
        if item.state is not PublicationState.PUBLISHED:
            raise BiaiceError("GATE_NOT_CURRENT", detail="Evaluation protocol is not published.")
        self._require_published_dataset(identity=identity, dataset_id=item.dataset_id)
        return item

    def create_calibration_artifact(
        self,
        *,
        identity: IdentityContext,
        command: CalibrationArtifactCreate,
        idempotency_key: str,
        request_id: str,
    ) -> CalibrationArtifactVersion:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> CalibrationArtifactVersion:
            self._require_published_model_artifact(
                identity=identity,
                model_artifact_id=command.model_artifact_id,
            )
            self._require_published_dataset(identity=identity, dataset_id=command.dataset_id)
            protocol = self._require_published_protocol(
                identity=identity,
                evaluation_protocol_id=command.evaluation_protocol_id,
            )
            if protocol.dataset_id != command.dataset_id:
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Calibration dataset does not match the evaluation protocol.",
                )
            calibration_artifact_id = uuid4()
            item = CalibrationArtifactVersion(
                calibration_artifact_id=calibration_artifact_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=CALIBRATION_ARTIFACTS,
                resource_id=calibration_artifact_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_calibration_artifact",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=CalibrationArtifactVersion,
            object_type="CalibrationArtifactVersion",
            object_id=lambda item: item.calibration_artifact_id,
            outcome=lambda item: "CREATED",
            command=create,
        )

    def list_calibration_artifacts(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[CalibrationArtifactVersion]:
        return self._list(
            identity=identity,
            collection=CALIBRATION_ARTIFACTS,
            expected_type=CalibrationArtifactVersion,
            resource_id=lambda item: item.calibration_artifact_id,
            limit=limit,
            cursor=cursor,
        )

    def get_calibration_artifact(
        self, *, identity: IdentityContext, calibration_artifact_id: UUID
    ) -> CalibrationArtifactVersion:
        return self._get(
            identity=identity,
            collection=CALIBRATION_ARTIFACTS,
            resource_id=calibration_artifact_id,
            expected_type=CalibrationArtifactVersion,
            label="Calibration artifact",
        )

    def _validate_approval_evidence(
        self,
        *,
        identity: IdentityContext,
        model_artifact_id: UUID,
        evaluation_protocol_id: UUID,
        calibration_artifact_id: UUID | None,
    ) -> None:
        self._require_published_model_artifact(
            identity=identity,
            model_artifact_id=model_artifact_id,
        )
        protocol = self._require_published_protocol(
            identity=identity,
            evaluation_protocol_id=evaluation_protocol_id,
        )
        if calibration_artifact_id is None:
            return
        calibration = self.get_calibration_artifact(
            identity=identity,
            calibration_artifact_id=calibration_artifact_id,
        )
        if (
            calibration.model_artifact_id != model_artifact_id
            or calibration.evaluation_protocol_id != evaluation_protocol_id
            or calibration.dataset_id != protocol.dataset_id
        ):
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Calibration evidence does not match the approval inputs.",
            )

    def create_model_approval(
        self,
        *,
        identity: IdentityContext,
        command: ModelApprovalCreate,
        idempotency_key: str,
        request_id: str,
    ) -> ModelApprovalVersion:
        _require_role(identity, *AUTHOR_ROLES, mfa=True)

        def create() -> ModelApprovalVersion:
            self._validate_approval_evidence(
                identity=identity,
                model_artifact_id=command.model_artifact_id,
                evaluation_protocol_id=command.evaluation_protocol_id,
                calibration_artifact_id=command.calibration_artifact_id,
            )
            now = self.clock.now()
            if command.expires_at is not None and command.expires_at <= now:
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Approval expiry must be in the future.",
                )
            model_approval_id = uuid4()
            item = ModelApprovalVersion(
                model_approval_id=model_approval_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                created_at=now,
                created_by=identity.subject_id,
                state=ApprovalState.PENDING,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=MODEL_APPROVALS,
                resource_id=model_approval_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_model_approval",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=ModelApprovalVersion,
            object_type="ModelApprovalVersion",
            object_id=lambda item: item.model_approval_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def get_model_approval(
        self, *, identity: IdentityContext, model_approval_id: UUID
    ) -> ModelApprovalVersion:
        return self._get(
            identity=identity,
            collection=MODEL_APPROVALS,
            resource_id=model_approval_id,
            expected_type=ModelApprovalVersion,
            label="Model approval",
        )

    def decide_model_approval(
        self,
        *,
        identity: IdentityContext,
        model_approval_id: UUID,
        command: ModelApprovalDecision,
        idempotency_key: str,
        request_id: str,
    ) -> ModelApprovalVersion:
        _require_role(identity, *APPROVER_ROLES, mfa=True)

        def decide() -> ModelApprovalVersion:
            item = self.get_model_approval(
                identity=identity,
                model_approval_id=model_approval_id,
            )
            if item.state is not ApprovalState.PENDING:
                raise BiaiceError("GATE_NOT_CURRENT", detail="Model approval is already terminal.")
            if item.created_by == identity.subject_id:
                raise BiaiceError(
                    "MAKER_CHECKER_REQUIRED",
                    detail="The approval author cannot decide the same model approval.",
                )
            if command.decision is ApprovalState.APPROVED:
                self._validate_approval_evidence(
                    identity=identity,
                    model_artifact_id=item.model_artifact_id,
                    evaluation_protocol_id=item.evaluation_protocol_id,
                    calibration_artifact_id=item.calibration_artifact_id,
                )
            decided = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": command.decision,
                    "decided_at": self.clock.now(),
                    "decided_by": identity.subject_id,
                    "decision_rationale": command.rationale,
                }
            )
            self.repository.upsert(
                collection=MODEL_APPROVALS,
                resource_id=model_approval_id,
                item=decided,
            )
            return decided

        return self._execute(
            identity=identity,
            operation_id="decide_model_approval",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(model_approval_id, command),
            expected_type=ModelApprovalVersion,
            object_type="ModelApprovalVersion",
            object_id=lambda item: item.model_approval_id,
            outcome=lambda item: item.state.value,
            command=decide,
        )

    def _require_approved_approval(
        self, *, identity: IdentityContext, model_approval_id: UUID
    ) -> ModelApprovalVersion:
        approval = self.get_model_approval(
            identity=identity,
            model_approval_id=model_approval_id,
        )
        if approval.state is not ApprovalState.APPROVED:
            raise BiaiceError("GATE_NOT_CURRENT", detail="Model approval is not approved.")
        if approval.expires_at is not None and self.clock.now() >= approval.expires_at:
            raise BiaiceError("GATE_NOT_CURRENT", detail="Model approval has expired.")
        self._validate_approval_evidence(
            identity=identity,
            model_artifact_id=approval.model_artifact_id,
            evaluation_protocol_id=approval.evaluation_protocol_id,
            calibration_artifact_id=approval.calibration_artifact_id,
        )
        return approval

    def _validate_deployment_binding(
        self,
        *,
        identity: IdentityContext,
        model_artifact_id: UUID,
        model_approval_id: UUID,
        provider_configuration_id: UUID,
        intended_purpose: str,
    ) -> tuple[ModelArtifactVersion, ModelApprovalVersion]:
        artifact = self._require_published_model_artifact(
            identity=identity,
            model_artifact_id=model_artifact_id,
        )
        approval = self._require_approved_approval(
            identity=identity,
            model_approval_id=model_approval_id,
        )
        if approval.model_artifact_id != artifact.model_artifact_id:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Deployment artifact does not match the approved artifact.",
            )
        if approval.intended_purpose != intended_purpose:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Deployment purpose does not match the approved purpose.",
            )
        self._require_external_model_reference(
            identity=identity,
            catalog_id=artifact.catalog_id,
            catalog_hash=artifact.catalog_hash,
            provider_id=artifact.provider_id,
            provider_model_id=artifact.provider_model_id,
            provider_configuration_id=provider_configuration_id,
        )
        return artifact, approval

    def create_model_deployment(
        self,
        *,
        identity: IdentityContext,
        command: ModelDeploymentCreate,
        idempotency_key: str,
        request_id: str,
    ) -> ModelDeploymentVersion:
        _require_role(identity, *DEPLOYER_ROLES, mfa=True)

        def create() -> ModelDeploymentVersion:
            self._validate_deployment_binding(
                identity=identity,
                model_artifact_id=command.model_artifact_id,
                model_approval_id=command.model_approval_id,
                provider_configuration_id=command.provider_configuration_id,
                intended_purpose=command.intended_purpose,
            )
            model_deployment_id = uuid4()
            item = ModelDeploymentVersion(
                model_deployment_id=model_deployment_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                state=DeploymentState.DRAFT,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=MODEL_DEPLOYMENTS,
                resource_id=model_deployment_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_model_deployment",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=ModelDeploymentVersion,
            object_type="ModelDeploymentVersion",
            object_id=lambda item: item.model_deployment_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def get_model_deployment(
        self, *, identity: IdentityContext, model_deployment_id: UUID
    ) -> ModelDeploymentVersion:
        return self._get(
            identity=identity,
            collection=MODEL_DEPLOYMENTS,
            resource_id=model_deployment_id,
            expected_type=ModelDeploymentVersion,
            label="Model deployment",
        )

    def activate_model_deployment(
        self,
        *,
        identity: IdentityContext,
        model_deployment_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> ModelDeploymentVersion:
        _require_role(identity, *DEPLOYER_ROLES, mfa=True)

        def activate() -> ModelDeploymentVersion:
            item = self.get_model_deployment(
                identity=identity,
                model_deployment_id=model_deployment_id,
            )
            if item.state is not DeploymentState.DRAFT:
                raise BiaiceError("GATE_NOT_CURRENT", detail="Deployment is not a draft.")
            self._validate_deployment_binding(
                identity=identity,
                model_artifact_id=item.model_artifact_id,
                model_approval_id=item.model_approval_id,
                provider_configuration_id=item.provider_configuration_id,
                intended_purpose=item.intended_purpose,
            )
            now = self.clock.now()
            active = self.repository.find_active_deployment(
                scope=identity.scope,
                deployment_slot=item.deployment_slot,
            )
            if active is not None:
                superseded = active.model_copy(
                    update={
                        "version_id": uuid4(),
                        "state": DeploymentState.SUPERSEDED,
                        "deactivated_at": now,
                        "deactivated_by": identity.subject_id,
                    }
                )
                self.repository.upsert(
                    collection=MODEL_DEPLOYMENTS,
                    resource_id=active.model_deployment_id,
                    item=superseded,
                )
            activated = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": DeploymentState.ACTIVE,
                    "supersedes_deployment_id": (
                        active.model_deployment_id if active is not None else None
                    ),
                    "activated_at": now,
                    "activated_by": identity.subject_id,
                }
            )
            self.repository.upsert(
                collection=MODEL_DEPLOYMENTS,
                resource_id=model_deployment_id,
                item=activated,
            )
            return activated

        return self._execute(
            identity=identity,
            operation_id="activate_model_deployment",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(model_deployment_id,),
            expected_type=ModelDeploymentVersion,
            object_type="ModelDeploymentVersion",
            object_id=lambda item: item.model_deployment_id,
            outcome=lambda item: item.state.value,
            command=activate,
        )

    def rollback_model_deployment(
        self,
        *,
        identity: IdentityContext,
        model_deployment_id: UUID,
        command: ModelDeploymentRollback,
        idempotency_key: str,
        request_id: str,
    ) -> ModelDeploymentVersion:
        _require_role(identity, *DEPLOYER_ROLES, mfa=True)

        def rollback() -> ModelDeploymentVersion:
            item = self.get_model_deployment(
                identity=identity,
                model_deployment_id=model_deployment_id,
            )
            if item.state is not DeploymentState.ACTIVE:
                raise BiaiceError("GATE_NOT_CURRENT", detail="Deployment is not active.")
            if item.supersedes_deployment_id is None:
                raise BiaiceError(
                    "GATE_NOT_CURRENT",
                    detail="Deployment has no superseded target to restore.",
                )
            target = self.get_model_deployment(
                identity=identity,
                model_deployment_id=item.supersedes_deployment_id,
            )
            if target.state is not DeploymentState.SUPERSEDED:
                raise BiaiceError(
                    "GATE_NOT_CURRENT",
                    detail="Rollback target is no longer superseded.",
                )
            self._validate_deployment_binding(
                identity=identity,
                model_artifact_id=target.model_artifact_id,
                model_approval_id=target.model_approval_id,
                provider_configuration_id=target.provider_configuration_id,
                intended_purpose=target.intended_purpose,
            )
            if command.model_incident_id is not None:
                incident = self.get_model_incident(
                    identity=identity,
                    model_incident_id=command.model_incident_id,
                )
                if incident.model_deployment_id != model_deployment_id:
                    raise BiaiceError(
                        "REQUEST_VALIDATION_FAILED",
                        detail="Rollback incident does not belong to this deployment.",
                    )
            now = self.clock.now()
            rolled_back = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": DeploymentState.ROLLED_BACK,
                    "deactivated_at": now,
                    "deactivated_by": identity.subject_id,
                }
            )
            restored = target.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": DeploymentState.ACTIVE,
                    "activated_at": now,
                    "activated_by": identity.subject_id,
                    "deactivated_at": None,
                    "deactivated_by": None,
                }
            )
            self.repository.upsert(
                collection=MODEL_DEPLOYMENTS,
                resource_id=model_deployment_id,
                item=rolled_back,
            )
            self.repository.upsert(
                collection=MODEL_DEPLOYMENTS,
                resource_id=target.model_deployment_id,
                item=restored,
            )
            rollback_event = self._new_rollback_event(
                identity=identity,
                command=RollbackEventCreate(
                    model_deployment_id=model_deployment_id,
                    from_model_artifact_id=item.model_artifact_id,
                    to_model_artifact_id=target.model_artifact_id,
                    model_incident_id=command.model_incident_id,
                    reason=command.reason,
                    evidence_hash=command.evidence_hash,
                ),
            )
            self.repository.upsert(
                collection=ROLLBACK_EVENTS,
                resource_id=rollback_event.rollback_event_id,
                item=rollback_event,
            )
            return rolled_back

        return self._execute(
            identity=identity,
            operation_id="rollback_model_deployment",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(model_deployment_id, command),
            expected_type=ModelDeploymentVersion,
            object_type="ModelDeploymentVersion",
            object_id=lambda item: item.model_deployment_id,
            outcome=lambda item: item.state.value,
            command=rollback,
        )

    def create_monitoring_snapshot(
        self,
        *,
        identity: IdentityContext,
        command: MonitoringSnapshotCreate,
        idempotency_key: str,
        request_id: str,
    ) -> ModelMonitoringSnapshot:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> ModelMonitoringSnapshot:
            deployment = self.get_model_deployment(
                identity=identity,
                model_deployment_id=command.model_deployment_id,
            )
            if deployment.state is not DeploymentState.ACTIVE:
                raise BiaiceError("GATE_NOT_CURRENT", detail="Deployment is not active.")
            approval = self.get_model_approval(
                identity=identity,
                model_approval_id=deployment.model_approval_id,
            )
            if approval.evaluation_protocol_id != command.evaluation_protocol_id:
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Monitoring protocol does not match the approved deployment.",
                )
            protocol = self._require_published_protocol(
                identity=identity,
                evaluation_protocol_id=command.evaluation_protocol_id,
            )
            expected_metrics = {metric.code for metric in protocol.metrics}
            if set(command.metric_values) != expected_metrics:
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Monitoring metrics must exactly match the evaluation protocol.",
                )
            monitoring_snapshot_id = uuid4()
            item = ModelMonitoringSnapshot(
                monitoring_snapshot_id=monitoring_snapshot_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=MONITORING_SNAPSHOTS,
                resource_id=monitoring_snapshot_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_monitoring_snapshot",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=ModelMonitoringSnapshot,
            object_type="ModelMonitoringSnapshot",
            object_id=lambda item: item.monitoring_snapshot_id,
            outcome=lambda item: item.drift_status.value,
            command=create,
        )

    def list_monitoring_snapshots(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[ModelMonitoringSnapshot]:
        return self._list(
            identity=identity,
            collection=MONITORING_SNAPSHOTS,
            expected_type=ModelMonitoringSnapshot,
            resource_id=lambda item: item.monitoring_snapshot_id,
            limit=limit,
            cursor=cursor,
        )

    def get_monitoring_snapshot(
        self, *, identity: IdentityContext, monitoring_snapshot_id: UUID
    ) -> ModelMonitoringSnapshot:
        return self._get(
            identity=identity,
            collection=MONITORING_SNAPSHOTS,
            resource_id=monitoring_snapshot_id,
            expected_type=ModelMonitoringSnapshot,
            label="Monitoring snapshot",
        )

    def create_model_incident(
        self,
        *,
        identity: IdentityContext,
        command: ModelIncidentCreate,
        idempotency_key: str,
        request_id: str,
    ) -> ModelIncidentEvent:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> ModelIncidentEvent:
            self.get_model_deployment(
                identity=identity,
                model_deployment_id=command.model_deployment_id,
            )
            if command.monitoring_snapshot_id is not None:
                snapshot = self.get_monitoring_snapshot(
                    identity=identity,
                    monitoring_snapshot_id=command.monitoring_snapshot_id,
                )
                if snapshot.model_deployment_id != command.model_deployment_id:
                    raise BiaiceError(
                        "REQUEST_VALIDATION_FAILED",
                        detail="Monitoring snapshot does not belong to the incident deployment.",
                    )
            model_incident_id = uuid4()
            item = ModelIncidentEvent(
                model_incident_id=model_incident_id,
                version_id=uuid4(),
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                created_at=self.clock.now(),
                created_by=identity.subject_id,
                state=IncidentState.OPEN,
                **command.model_dump(),
            )
            self.repository.upsert(
                collection=MODEL_INCIDENTS,
                resource_id=model_incident_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_model_incident",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=ModelIncidentEvent,
            object_type="ModelIncidentEvent",
            object_id=lambda item: item.model_incident_id,
            outcome=lambda item: item.state.value,
            command=create,
        )

    def list_model_incidents(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[ModelIncidentEvent]:
        return self._list(
            identity=identity,
            collection=MODEL_INCIDENTS,
            expected_type=ModelIncidentEvent,
            resource_id=lambda item: item.model_incident_id,
            limit=limit,
            cursor=cursor,
        )

    def get_model_incident(
        self, *, identity: IdentityContext, model_incident_id: UUID
    ) -> ModelIncidentEvent:
        return self._get(
            identity=identity,
            collection=MODEL_INCIDENTS,
            resource_id=model_incident_id,
            expected_type=ModelIncidentEvent,
            label="Model incident",
        )

    def _validate_rollback_references(
        self, *, identity: IdentityContext, command: RollbackEventCreate
    ) -> None:
        deployment = self.get_model_deployment(
            identity=identity,
            model_deployment_id=command.model_deployment_id,
        )
        if deployment.model_artifact_id != command.from_model_artifact_id:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="Rollback source artifact does not match the deployment.",
            )
        if command.to_model_artifact_id is not None:
            self._require_published_model_artifact(
                identity=identity,
                model_artifact_id=command.to_model_artifact_id,
            )
        if command.model_incident_id is not None:
            incident = self.get_model_incident(
                identity=identity,
                model_incident_id=command.model_incident_id,
            )
            if incident.model_deployment_id != command.model_deployment_id:
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Rollback incident does not belong to the deployment.",
                )

    def _new_rollback_event(
        self, *, identity: IdentityContext, command: RollbackEventCreate
    ) -> RollbackEvent:
        return RollbackEvent(
            rollback_event_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            created_at=self.clock.now(),
            created_by=identity.subject_id,
            **command.model_dump(),
        )

    def create_rollback_event(
        self,
        *,
        identity: IdentityContext,
        command: RollbackEventCreate,
        idempotency_key: str,
        request_id: str,
    ) -> RollbackEvent:
        _require_role(identity, *AUTHOR_ROLES)

        def create() -> RollbackEvent:
            self._validate_rollback_references(identity=identity, command=command)
            item = self._new_rollback_event(identity=identity, command=command)
            self.repository.upsert(
                collection=ROLLBACK_EVENTS,
                resource_id=item.rollback_event_id,
                item=item,
            )
            return item

        return self._execute(
            identity=identity,
            operation_id="create_rollback_event",
            idempotency_key=idempotency_key,
            request_id=request_id,
            fingerprint_values=(command,),
            expected_type=RollbackEvent,
            object_type="RollbackEvent",
            object_id=lambda item: item.rollback_event_id,
            outcome=lambda item: "CREATED",
            command=create,
        )

    def list_rollback_events(
        self,
        *,
        identity: IdentityContext,
        limit: int = 100,
        cursor: str | None = None,
    ) -> ModelLifecyclePage[RollbackEvent]:
        return self._list(
            identity=identity,
            collection=ROLLBACK_EVENTS,
            expected_type=RollbackEvent,
            resource_id=lambda item: item.rollback_event_id,
            limit=limit,
            cursor=cursor,
        )

    def get_rollback_event(
        self, *, identity: IdentityContext, rollback_event_id: UUID
    ) -> RollbackEvent:
        return self._get(
            identity=identity,
            collection=ROLLBACK_EVENTS,
            resource_id=rollback_event_id,
            expected_type=RollbackEvent,
            label="Rollback event",
        )


def configure_model_lifecycle(
    app,
    *,
    repository: InMemoryModelLifecycleRepository | None = None,
    clock: Clock | None = None,
) -> ModelLifecycleService:
    """Attach the synthetic FR-13 repository and service to application state."""
    repository = repository or InMemoryModelLifecycleRepository()
    configured = app.state.settings.cursor_hmac_key
    raw_secret = (
        configured.get_secret_value().encode("utf-8")
        if configured is not None
        else secrets.token_bytes(32)
    )
    service = ModelLifecycleService(
        repository=repository,
        clock=clock or SystemClock(),
        audit_writer=app.state.audit_writer,
        cursor_codec=CursorCodec(hashlib.sha256(raw_secret).digest()),
    )
    app.state.model_lifecycle_repository = repository
    app.state.model_lifecycle_service = service
    return service
