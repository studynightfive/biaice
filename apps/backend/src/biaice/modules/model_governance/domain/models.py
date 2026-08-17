"""Typed, immutable FR-13 model-governance contracts.

``ModelArtifactVersion`` deliberately stores only an external Provider/model
reference and reproducibility evidence. It never accepts model weights, API
keys, arbitrary endpoints, prompts, or provider response payloads.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    field_validator,
    model_validator,
)

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
FiniteFloat = Annotated[StrictFloat, Field(allow_inf_nan=False)]
NonNegativeFloat = Annotated[StrictFloat, Field(ge=0, allow_inf_nan=False)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PublicationState(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class FeatureDataType(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    CATEGORY = "CATEGORY"
    DATETIME = "DATETIME"


class MetricDirection(StrEnum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"
    TARGET = "TARGET"


class CalibrationPurpose(StrEnum):
    REVIEW_OUTCOME_MODEL = "REVIEW_OUTCOME_MODEL"
    FIRST_CANDIDATE = "FIRST_CANDIDATE"


class DriftStatus(StrEnum):
    NO_DRIFT = "NO_DRIFT"
    WATCH = "WATCH"
    BREACH = "BREACH"


class IncidentSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentState(StrEnum):
    OPEN = "OPEN"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"


class ApprovalState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DeploymentState(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ROLLED_BACK = "ROLLED_BACK"


class ScopedVersion(FrozenModel):
    version_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    created_at: datetime
    created_by: UUID


class PublishableVersion(ScopedVersion):
    state: PublicationState
    published_at: datetime | None = None
    published_by: UUID | None = None

    @model_validator(mode="after")
    def publication_metadata_matches_state(self) -> "PublishableVersion":
        published = self.published_at is not None and self.published_by is not None
        if self.state is PublicationState.PUBLISHED and not published:
            raise ValueError("published resources require publication metadata")
        if self.state is PublicationState.DRAFT and (
            self.published_at is not None or self.published_by is not None
        ):
            raise ValueError("draft resources cannot contain publication metadata")
        return self


class DatasetSnapshotCreate(FrozenModel):
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=120)
    source_asset_ids: tuple[UUID, ...] = Field(min_length=1)
    row_count: int = Field(ge=0)
    content_hash: Sha256
    observed_from: datetime | None = None
    observed_until: datetime | None = None

    @field_validator("row_count", mode="before")
    @classmethod
    def row_count_is_not_boolean(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("row_count must be an integer")
        return value

    @model_validator(mode="after")
    def dataset_evidence_is_consistent(self) -> "DatasetSnapshotCreate":
        if len(set(self.source_asset_ids)) != len(self.source_asset_ids):
            raise ValueError("source_asset_ids must be unique")
        if (self.observed_from is None) != (self.observed_until is None):
            raise ValueError("observed_from and observed_until must be provided together")
        if (
            self.observed_from is not None
            and self.observed_until is not None
            and self.observed_until <= self.observed_from
        ):
            raise ValueError("observed_until must be later than observed_from")
        return self

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        schema = handler(core_schema)
        schema["properties"]["source_asset_ids"]["uniqueItems"] = True
        return schema


class DatasetSnapshotVersion(PublishableVersion):
    dataset_id: UUID
    name: str
    purpose: str
    source_asset_ids: tuple[UUID, ...]
    row_count: int
    content_hash: Sha256
    observed_from: datetime | None = None
    observed_until: datetime | None = None


class FeatureDefinition(FrozenModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    data_type: FeatureDataType
    nullable: StrictBool = False
    description: str | None = Field(default=None, max_length=500)
    allowed_values: tuple[str, ...] = Field(default_factory=tuple, max_length=500)

    @field_validator("allowed_values")
    @classmethod
    def allowed_values_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("allowed_values must be unique")
        return value


class FeatureSchemaCreate(FrozenModel):
    name: str = Field(min_length=1, max_length=200)
    features: tuple[FeatureDefinition, ...] = Field(min_length=1)
    schema_hash: Sha256

    @field_validator("features")
    @classmethod
    def feature_names_are_unique(
        cls, value: tuple[FeatureDefinition, ...]
    ) -> tuple[FeatureDefinition, ...]:
        names = [feature.name for feature in value]
        if len(set(names)) != len(names):
            raise ValueError("feature names must be unique")
        return value


class FeatureSchemaVersion(PublishableVersion):
    feature_schema_id: UUID
    name: str
    features: tuple[FeatureDefinition, ...]
    schema_hash: Sha256


class ModelArtifactCreate(FrozenModel):
    name: str = Field(min_length=1, max_length=200)
    feature_schema_id: UUID
    catalog_id: UUID
    catalog_hash: Sha256
    provider_id: str = Field(min_length=1, max_length=120)
    provider_model_id: str = Field(min_length=1, max_length=200)
    adapter_version: str = Field(min_length=1, max_length=120)
    api_version: str | None = Field(default=None, max_length=120)
    code_or_image_digest: Sha256
    prompt_template_id: UUID
    prompt_template_hash: Sha256
    parameter_schema_hash: Sha256
    dependency_lock_hash: Sha256
    evaluation_evidence_hash: Sha256
    randomness_protocol: str = Field(min_length=1, max_length=500)
    numeric_protocol: str = Field(min_length=1, max_length=500)


class ModelArtifactVersion(PublishableVersion):
    model_artifact_id: UUID
    name: str
    feature_schema_id: UUID
    catalog_id: UUID
    catalog_hash: Sha256
    provider_id: str
    provider_model_id: str
    adapter_version: str
    api_version: str | None = None
    code_or_image_digest: Sha256
    prompt_template_id: UUID
    prompt_template_hash: Sha256
    parameter_schema_hash: Sha256
    dependency_lock_hash: Sha256
    evaluation_evidence_hash: Sha256
    randomness_protocol: str
    numeric_protocol: str


class EvaluationMetricDefinition(FrozenModel):
    code: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    direction: MetricDirection
    threshold: FiniteFloat | None = None
    target_value: FiniteFloat | None = None

    @model_validator(mode="after")
    def target_value_matches_direction(self) -> "EvaluationMetricDefinition":
        if self.direction is MetricDirection.TARGET and self.target_value is None:
            raise ValueError("TARGET metrics require target_value")
        if self.direction is not MetricDirection.TARGET and self.target_value is not None:
            raise ValueError("target_value is only valid for TARGET metrics")
        return self


class EvaluationProtocolCreate(FrozenModel):
    name: str = Field(min_length=1, max_length=200)
    dataset_id: UUID
    metrics: tuple[EvaluationMetricDefinition, ...] = Field(min_length=1)
    absolute_tolerance: NonNegativeFloat
    relative_tolerance: NonNegativeFloat
    aggregation_protocol: str = Field(min_length=1, max_length=1000)
    cluster_unit: Literal["DECISION_UNIT", "PROJECT", "BUYER"]

    @field_validator("metrics")
    @classmethod
    def metric_codes_are_unique(
        cls, value: tuple[EvaluationMetricDefinition, ...]
    ) -> tuple[EvaluationMetricDefinition, ...]:
        codes = [metric.code for metric in value]
        if len(set(codes)) != len(codes):
            raise ValueError("metric codes must be unique")
        return value

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        schema = handler(core_schema)
        schema["properties"]["metrics"]["uniqueItems"] = True
        return schema


class EvaluationProtocolVersion(PublishableVersion):
    evaluation_protocol_id: UUID
    name: str
    dataset_id: UUID
    metrics: tuple[EvaluationMetricDefinition, ...]
    absolute_tolerance: NonNegativeFloat
    relative_tolerance: NonNegativeFloat
    aggregation_protocol: str
    cluster_unit: Literal["DECISION_UNIT", "PROJECT", "BUYER"]


class CalibrationArtifactCreate(FrozenModel):
    model_artifact_id: UUID
    dataset_id: UUID
    evaluation_protocol_id: UUID
    purpose: CalibrationPurpose
    method: str = Field(min_length=1, max_length=200)
    artifact_hash: Sha256
    evaluation_evidence_hash: Sha256


class CalibrationArtifactVersion(ScopedVersion):
    calibration_artifact_id: UUID
    model_artifact_id: UUID
    dataset_id: UUID
    evaluation_protocol_id: UUID
    purpose: CalibrationPurpose
    method: str
    artifact_hash: Sha256
    evaluation_evidence_hash: Sha256


class MonitoringSnapshotCreate(FrozenModel):
    model_deployment_id: UUID
    evaluation_protocol_id: UUID
    window_start: datetime
    window_end: datetime
    sample_count: int = Field(ge=0)
    metric_values: dict[str, FiniteFloat] = Field(min_length=1, max_length=200)
    drift_status: DriftStatus
    evidence_hash: Sha256

    @field_validator("sample_count", mode="before")
    @classmethod
    def sample_count_is_not_boolean(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("sample_count must be an integer")
        return value

    @model_validator(mode="after")
    def monitoring_window_is_ordered(self) -> "MonitoringSnapshotCreate":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be later than window_start")
        return self


class ModelMonitoringSnapshot(ScopedVersion):
    monitoring_snapshot_id: UUID
    model_deployment_id: UUID
    evaluation_protocol_id: UUID
    window_start: datetime
    window_end: datetime
    sample_count: int
    metric_values: dict[str, FiniteFloat]
    drift_status: DriftStatus
    evidence_hash: Sha256


class ModelIncidentCreate(FrozenModel):
    model_deployment_id: UUID
    monitoring_snapshot_id: UUID | None = None
    severity: IncidentSeverity
    summary: str = Field(min_length=1, max_length=1000)
    detected_at: datetime
    evidence_hash: Sha256


class ModelIncidentEvent(ScopedVersion):
    model_incident_id: UUID
    model_deployment_id: UUID
    monitoring_snapshot_id: UUID | None = None
    severity: IncidentSeverity
    state: IncidentState
    summary: str
    detected_at: datetime
    evidence_hash: Sha256


class RollbackEventCreate(FrozenModel):
    model_deployment_id: UUID
    from_model_artifact_id: UUID
    to_model_artifact_id: UUID | None = None
    model_incident_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=1000)
    evidence_hash: Sha256


class RollbackEvent(ScopedVersion):
    rollback_event_id: UUID
    model_deployment_id: UUID
    from_model_artifact_id: UUID
    to_model_artifact_id: UUID | None = None
    model_incident_id: UUID | None = None
    reason: str
    evidence_hash: Sha256


class ModelApprovalCreate(FrozenModel):
    model_artifact_id: UUID
    evaluation_protocol_id: UUID
    calibration_artifact_id: UUID | None = None
    intended_purpose: str = Field(min_length=1, max_length=200)
    evidence_hash: Sha256
    expires_at: datetime | None = None


class ModelApprovalDecision(FrozenModel):
    decision: Literal[ApprovalState.APPROVED, ApprovalState.REJECTED]
    rationale: str = Field(min_length=1, max_length=2000)


class ModelApprovalVersion(ScopedVersion):
    model_approval_id: UUID
    model_artifact_id: UUID
    evaluation_protocol_id: UUID
    calibration_artifact_id: UUID | None = None
    intended_purpose: str
    evidence_hash: Sha256
    state: ApprovalState
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by: UUID | None = None
    decision_rationale: str | None = None

    @model_validator(mode="after")
    def decision_metadata_matches_state(self) -> "ModelApprovalVersion":
        decided = (
            self.decided_at is not None
            and self.decided_by is not None
            and self.decision_rationale is not None
        )
        if self.state is ApprovalState.PENDING and (
            self.decided_at is not None
            or self.decided_by is not None
            or self.decision_rationale is not None
        ):
            raise ValueError("pending approval cannot contain decision metadata")
        if self.state is not ApprovalState.PENDING and not decided:
            raise ValueError("terminal approval requires decision metadata")
        return self


class ModelDeploymentCreate(FrozenModel):
    model_artifact_id: UUID
    model_approval_id: UUID
    provider_configuration_id: UUID
    deployment_slot: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$",
    )
    intended_purpose: str = Field(min_length=1, max_length=200)


class ModelDeploymentRollback(FrozenModel):
    reason: str = Field(min_length=1, max_length=1000)
    evidence_hash: Sha256
    model_incident_id: UUID | None = None


class ModelDeploymentVersion(ScopedVersion):
    model_deployment_id: UUID
    model_artifact_id: UUID
    model_approval_id: UUID
    provider_configuration_id: UUID
    deployment_slot: str
    intended_purpose: str
    state: DeploymentState
    supersedes_deployment_id: UUID | None = None
    activated_at: datetime | None = None
    activated_by: UUID | None = None
    deactivated_at: datetime | None = None
    deactivated_by: UUID | None = None

    @model_validator(mode="after")
    def lifecycle_metadata_matches_state(self) -> "ModelDeploymentVersion":
        activated = self.activated_at is not None and self.activated_by is not None
        deactivated = self.deactivated_at is not None and self.deactivated_by is not None
        if self.state is DeploymentState.DRAFT and (activated or deactivated):
            raise ValueError("draft deployment cannot contain transition metadata")
        if self.state is DeploymentState.ACTIVE and (not activated or deactivated):
            raise ValueError("active deployment requires activation and no deactivation")
        if self.state in {DeploymentState.SUPERSEDED, DeploymentState.ROLLED_BACK} and (
            not activated or not deactivated
        ):
            raise ValueError("inactive deployment requires activation and deactivation metadata")
        return self
