"""Typed FR-13 datasets, artifacts, approvals, deployments and monitoring API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import IdentityContext, get_identity
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.http import CursorPage
from biaice.core.idempotency import require_idempotency_key
from biaice.modules.model_governance.application.model_lifecycle import (
    ModelLifecycleService,
)
from biaice.modules.model_governance.domain.models import (
    CalibrationArtifactCreate,
    CalibrationArtifactVersion,
    DatasetSnapshotCreate,
    DatasetSnapshotVersion,
    EvaluationProtocolCreate,
    EvaluationProtocolVersion,
    FeatureSchemaCreate,
    FeatureSchemaVersion,
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
    RollbackEvent,
    RollbackEventCreate,
)

router = APIRouter(prefix="/api/v1", tags=["FR-13", "model-lifecycle"])
IDEMPOTENT_OPERATION = {"x-idempotency-required": True}
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageCursor = Annotated[str | None, Query(min_length=1, max_length=4096)]


class StrictPageQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=200)
    cursor: str | None = Field(default=None, min_length=1, max_length=4096)


MODEL_LIFECYCLE_OPERATION_IDS = frozenset(
    {
        "list_datasets",
        "create_dataset",
        "get_dataset",
        "publish_dataset",
        "list_feature_schemas",
        "create_feature_schema",
        "get_feature_schema",
        "publish_feature_schema",
        "list_model_artifacts",
        "create_model_artifact",
        "get_model_artifact",
        "publish_model_artifact",
        "list_evaluation_protocols",
        "create_evaluation_protocol",
        "get_evaluation_protocol",
        "publish_evaluation_protocol",
        "list_calibration_artifacts",
        "create_calibration_artifact",
        "get_calibration_artifact",
        "list_monitoring_snapshots",
        "create_monitoring_snapshot",
        "get_monitoring_snapshot",
        "list_model_incidents",
        "create_model_incident",
        "get_model_incident",
        "list_rollback_events",
        "create_rollback_event",
        "get_rollback_event",
        "create_model_approval",
        "decide_model_approval",
        "create_model_deployment",
        "activate_model_deployment",
        "rollback_model_deployment",
    }
)


class DatasetListResponse(CursorPage):
    items: tuple[DatasetSnapshotVersion, ...]


class FeatureSchemaListResponse(CursorPage):
    items: tuple[FeatureSchemaVersion, ...]


class ModelArtifactListResponse(CursorPage):
    items: tuple[ModelArtifactVersion, ...]


class EvaluationProtocolListResponse(CursorPage):
    items: tuple[EvaluationProtocolVersion, ...]


class CalibrationArtifactListResponse(CursorPage):
    items: tuple[CalibrationArtifactVersion, ...]


class MonitoringSnapshotListResponse(CursorPage):
    items: tuple[ModelMonitoringSnapshot, ...]


class ModelIncidentListResponse(CursorPage):
    items: tuple[ModelIncidentEvent, ...]


class RollbackEventListResponse(CursorPage):
    items: tuple[RollbackEvent, ...]


def get_service(request: Request) -> ModelLifecycleService:
    service = getattr(request.app.state, "model_lifecycle_service", None)
    if service is None:
        raise BiaiceError("INTERNAL_ERROR", detail="Model lifecycle service is not configured.")
    return service


@router.get(
    "/datasets",
    operation_id="list_datasets",
    response_model=DatasetListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_datasets(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> DatasetListResponse:
    page = service.list_datasets(identity=identity, limit=query.limit, cursor=query.cursor)
    return DatasetListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/datasets",
    operation_id="create_dataset",
    response_model=DatasetSnapshotVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_dataset(
    body: DatasetSnapshotCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> DatasetSnapshotVersion:
    return service.create_dataset(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/datasets/{dataset_id}",
    operation_id="get_dataset",
    response_model=DatasetSnapshotVersion,
    responses=PROBLEM_RESPONSES,
)
def get_dataset(
    dataset_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> DatasetSnapshotVersion:
    return service.get_dataset(identity=identity, dataset_id=dataset_id)


@router.post(
    "/datasets/{dataset_id}/publish",
    operation_id="publish_dataset",
    response_model=DatasetSnapshotVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_dataset(
    dataset_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> DatasetSnapshotVersion:
    return service.publish_dataset(
        identity=identity,
        dataset_id=dataset_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/feature-schemas",
    operation_id="list_feature_schemas",
    response_model=FeatureSchemaListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_feature_schemas(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> FeatureSchemaListResponse:
    page = service.list_feature_schemas(identity=identity, limit=query.limit, cursor=query.cursor)
    return FeatureSchemaListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/feature-schemas",
    operation_id="create_feature_schema",
    response_model=FeatureSchemaVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_feature_schema(
    body: FeatureSchemaCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> FeatureSchemaVersion:
    return service.create_feature_schema(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/feature-schemas/{feature_schema_id}",
    operation_id="get_feature_schema",
    response_model=FeatureSchemaVersion,
    responses=PROBLEM_RESPONSES,
)
def get_feature_schema(
    feature_schema_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> FeatureSchemaVersion:
    return service.get_feature_schema(
        identity=identity,
        feature_schema_id=feature_schema_id,
    )


@router.post(
    "/feature-schemas/{feature_schema_id}/publish",
    operation_id="publish_feature_schema",
    response_model=FeatureSchemaVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_feature_schema(
    feature_schema_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> FeatureSchemaVersion:
    return service.publish_feature_schema(
        identity=identity,
        feature_schema_id=feature_schema_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/model-artifacts",
    operation_id="list_model_artifacts",
    response_model=ModelArtifactListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_model_artifacts(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelArtifactListResponse:
    page = service.list_model_artifacts(identity=identity, limit=query.limit, cursor=query.cursor)
    return ModelArtifactListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/model-artifacts",
    operation_id="create_model_artifact",
    response_model=ModelArtifactVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_model_artifact(
    body: ModelArtifactCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelArtifactVersion:
    return service.create_model_artifact(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/model-artifacts/{model_artifact_id}",
    operation_id="get_model_artifact",
    response_model=ModelArtifactVersion,
    responses=PROBLEM_RESPONSES,
)
def get_model_artifact(
    model_artifact_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelArtifactVersion:
    return service.get_model_artifact(
        identity=identity,
        model_artifact_id=model_artifact_id,
    )


@router.post(
    "/model-artifacts/{model_artifact_id}/publish",
    operation_id="publish_model_artifact",
    response_model=ModelArtifactVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_model_artifact(
    model_artifact_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelArtifactVersion:
    return service.publish_model_artifact(
        identity=identity,
        model_artifact_id=model_artifact_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/evaluation-protocols",
    operation_id="list_evaluation_protocols",
    response_model=EvaluationProtocolListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_evaluation_protocols(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> EvaluationProtocolListResponse:
    page = service.list_evaluation_protocols(
        identity=identity,
        limit=query.limit,
        cursor=query.cursor,
    )
    return EvaluationProtocolListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/evaluation-protocols",
    operation_id="create_evaluation_protocol",
    response_model=EvaluationProtocolVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_evaluation_protocol(
    body: EvaluationProtocolCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> EvaluationProtocolVersion:
    return service.create_evaluation_protocol(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/evaluation-protocols/{evaluation_protocol_id}",
    operation_id="get_evaluation_protocol",
    response_model=EvaluationProtocolVersion,
    responses=PROBLEM_RESPONSES,
)
def get_evaluation_protocol(
    evaluation_protocol_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> EvaluationProtocolVersion:
    return service.get_evaluation_protocol(
        identity=identity,
        evaluation_protocol_id=evaluation_protocol_id,
    )


@router.post(
    "/evaluation-protocols/{evaluation_protocol_id}/publish",
    operation_id="publish_evaluation_protocol",
    response_model=EvaluationProtocolVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def publish_evaluation_protocol(
    evaluation_protocol_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> EvaluationProtocolVersion:
    return service.publish_evaluation_protocol(
        identity=identity,
        evaluation_protocol_id=evaluation_protocol_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/calibration-artifacts",
    operation_id="list_calibration_artifacts",
    response_model=CalibrationArtifactListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_calibration_artifacts(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> CalibrationArtifactListResponse:
    page = service.list_calibration_artifacts(
        identity=identity,
        limit=query.limit,
        cursor=query.cursor,
    )
    return CalibrationArtifactListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/calibration-artifacts",
    operation_id="create_calibration_artifact",
    response_model=CalibrationArtifactVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_calibration_artifact(
    body: CalibrationArtifactCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> CalibrationArtifactVersion:
    return service.create_calibration_artifact(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/calibration-artifacts/{calibration_artifact_id}",
    operation_id="get_calibration_artifact",
    response_model=CalibrationArtifactVersion,
    responses=PROBLEM_RESPONSES,
)
def get_calibration_artifact(
    calibration_artifact_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> CalibrationArtifactVersion:
    return service.get_calibration_artifact(
        identity=identity,
        calibration_artifact_id=calibration_artifact_id,
    )


@router.get(
    "/monitoring-snapshots",
    operation_id="list_monitoring_snapshots",
    response_model=MonitoringSnapshotListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_monitoring_snapshots(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> MonitoringSnapshotListResponse:
    page = service.list_monitoring_snapshots(
        identity=identity,
        limit=query.limit,
        cursor=query.cursor,
    )
    return MonitoringSnapshotListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/monitoring-snapshots",
    operation_id="create_monitoring_snapshot",
    response_model=ModelMonitoringSnapshot,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_monitoring_snapshot(
    body: MonitoringSnapshotCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelMonitoringSnapshot:
    return service.create_monitoring_snapshot(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/monitoring-snapshots/{monitoring_snapshot_id}",
    operation_id="get_monitoring_snapshot",
    response_model=ModelMonitoringSnapshot,
    responses=PROBLEM_RESPONSES,
)
def get_monitoring_snapshot(
    monitoring_snapshot_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelMonitoringSnapshot:
    return service.get_monitoring_snapshot(
        identity=identity,
        monitoring_snapshot_id=monitoring_snapshot_id,
    )


@router.get(
    "/model-incidents",
    operation_id="list_model_incidents",
    response_model=ModelIncidentListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_model_incidents(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelIncidentListResponse:
    page = service.list_model_incidents(identity=identity, limit=query.limit, cursor=query.cursor)
    return ModelIncidentListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/model-incidents",
    operation_id="create_model_incident",
    response_model=ModelIncidentEvent,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_model_incident(
    body: ModelIncidentCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelIncidentEvent:
    return service.create_model_incident(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/model-incidents/{model_incident_id}",
    operation_id="get_model_incident",
    response_model=ModelIncidentEvent,
    responses=PROBLEM_RESPONSES,
)
def get_model_incident(
    model_incident_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelIncidentEvent:
    return service.get_model_incident(
        identity=identity,
        model_incident_id=model_incident_id,
    )


@router.get(
    "/rollback-events",
    operation_id="list_rollback_events",
    response_model=RollbackEventListResponse,
    responses=PROBLEM_RESPONSES,
)
def list_rollback_events(
    query: Annotated[StrictPageQuery, Query()],
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> RollbackEventListResponse:
    page = service.list_rollback_events(identity=identity, limit=query.limit, cursor=query.cursor)
    return RollbackEventListResponse(
        items=page.items,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post(
    "/rollback-events",
    operation_id="create_rollback_event",
    response_model=RollbackEvent,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_rollback_event(
    body: RollbackEventCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> RollbackEvent:
    return service.create_rollback_event(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.get(
    "/rollback-events/{rollback_event_id}",
    operation_id="get_rollback_event",
    response_model=RollbackEvent,
    responses=PROBLEM_RESPONSES,
)
def get_rollback_event(
    rollback_event_id: UUID,
    identity: IdentityContext = Depends(get_identity),
    service: ModelLifecycleService = Depends(get_service),
) -> RollbackEvent:
    return service.get_rollback_event(
        identity=identity,
        rollback_event_id=rollback_event_id,
    )


@router.post(
    "/model-approvals",
    operation_id="create_model_approval",
    response_model=ModelApprovalVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_model_approval(
    body: ModelApprovalCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelApprovalVersion:
    return service.create_model_approval(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/model-approvals/{model_approval_id}/decide",
    operation_id="decide_model_approval",
    response_model=ModelApprovalVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def decide_model_approval(
    model_approval_id: UUID,
    body: ModelApprovalDecision,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelApprovalVersion:
    return service.decide_model_approval(
        identity=identity,
        model_approval_id=model_approval_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/model-deployments",
    operation_id="create_model_deployment",
    response_model=ModelDeploymentVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def create_model_deployment(
    body: ModelDeploymentCreate,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelDeploymentVersion:
    return service.create_model_deployment(
        identity=identity,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/model-deployments/{model_deployment_id}/activate",
    operation_id="activate_model_deployment",
    response_model=ModelDeploymentVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def activate_model_deployment(
    model_deployment_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelDeploymentVersion:
    return service.activate_model_deployment(
        identity=identity,
        model_deployment_id=model_deployment_id,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )


@router.post(
    "/model-deployments/{model_deployment_id}/rollback",
    operation_id="rollback_model_deployment",
    response_model=ModelDeploymentVersion,
    responses=PROBLEM_RESPONSES,
    openapi_extra=IDEMPOTENT_OPERATION,
)
def rollback_model_deployment(
    model_deployment_id: UUID,
    body: ModelDeploymentRollback,
    request: Request,
    identity: IdentityContext = Depends(get_identity),
    idempotency_key: str = Depends(require_idempotency_key),
    service: ModelLifecycleService = Depends(get_service),
) -> ModelDeploymentVersion:
    return service.rollback_model_deployment(
        identity=identity,
        model_deployment_id=model_deployment_id,
        command=body,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
