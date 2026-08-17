// Generated from openapi.generated.json. Do not edit.
/* eslint-disable */

export interface AIProviderConfiguration {
  readonly config_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly version_number: number;
  readonly current: boolean;
  readonly catalog_id: string;
  readonly catalog_hash: string;
  readonly provider_id: string;
  readonly provider_model_id: string;
  readonly purpose: string;
  readonly monthly_budget_minor: number;
  readonly currency: string;
  readonly timeout_seconds: number;
  readonly retention_days: number;
  readonly legal_basis_evidence_id: string;
  readonly provider_policy_id: string;
  readonly pia_record_id: string;
  readonly cross_border_assessment_id: string;
  readonly activation_state: ProviderActivationState;
  readonly credential_state: ProviderCredentialState;
  readonly credential_usage_scope: CredentialUsageScope;
  readonly credential?: ProviderCredentialMetadata | null;
  readonly provider_health: ProviderHealth;
  readonly validity_state: ProviderValidity;
  readonly gate_reason_codes?: ReadonlyArray<string>;
  readonly supersedes_config_id?: string | null;
  readonly rotation_mode?: ProviderRotationMode | null;
  readonly state_version: number;
  readonly created_at: string;
  readonly created_by: string;
  readonly updated_at: string;
  readonly updated_by: string;
  readonly last_tested_at?: string | null;
}

export interface ActionRequest {
  readonly reason_code?: string;
  readonly notes?: string | null;
}

export type AdapterOwner = "MEMBER_1_GOVERNANCE" | "MEMBER_3_LOCAL_REPLICA" | "MEMBER_5_PROVIDER_REPLICA";

export type ApprovalState = "PENDING" | "APPROVED" | "REJECTED";

export interface ArchiveCompetitorRequest {
  readonly reason: string;
}

export interface BuildCompetitorProfileRequest {
  readonly source_ids: ReadonlyArray<string>;
  readonly participation_assumptions?: Record<string, number>;
  readonly bid_assumptions?: Record<string, number>;
  readonly potential_response_states?: ReadonlyArray<string>;
  readonly subjective_variables?: Record<string, number>;
  readonly validity_assumptions?: ReadonlyArray<string>;
  readonly coverage_notes: string;
  readonly bias_notes: string;
  readonly drift_notes: string;
  readonly data_quality: string;
}

export interface CalibrationArtifactCreate {
  readonly model_artifact_id: string;
  readonly dataset_id: string;
  readonly evaluation_protocol_id: string;
  readonly purpose: CalibrationPurpose;
  readonly method: string;
  readonly artifact_hash: string;
  readonly evaluation_evidence_hash: string;
}

export interface CalibrationArtifactListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<CalibrationArtifactVersion>;
}

export interface CalibrationArtifactVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly calibration_artifact_id: string;
  readonly model_artifact_id: string;
  readonly dataset_id: string;
  readonly evaluation_protocol_id: string;
  readonly purpose: CalibrationPurpose;
  readonly method: string;
  readonly artifact_hash: string;
  readonly evaluation_evidence_hash: string;
}

export type CalibrationPurpose = "REVIEW_OUTCOME_MODEL" | "FIRST_CANDIDATE";

export interface Competitor {
  readonly competitor_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly canonical_subject_key: string;
  readonly legal_name: string;
  readonly aliases?: ReadonlyArray<string>;
  readonly actor_id: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly archived_at?: string | null;
  readonly archive_reason?: string | null;
}

export interface CompetitorListResponse {
  readonly items: ReadonlyArray<Competitor>;
}

export interface CompetitorProfile {
  readonly profile_id: string;
  readonly version_id?: string;
  readonly competitor_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly source_ids: ReadonlyArray<string>;
  readonly participation_assumptions?: Record<string, number>;
  readonly bid_assumptions?: Record<string, number>;
  readonly potential_response_states?: ReadonlyArray<string>;
  readonly subjective_variables?: Record<string, number>;
  readonly validity_assumptions?: ReadonlyArray<string>;
  readonly coverage_notes: string;
  readonly bias_notes: string;
  readonly drift_notes: string;
  readonly data_quality: string;
  readonly state?: biaice__modules__market__domain__models__PublicationState;
  readonly actor_id?: string | null;
  readonly created_at: string;
  readonly updated_at?: string | null;
  readonly published_at?: string | null;
}

export interface CompetitorProfileListResponse {
  readonly items: ReadonlyArray<CompetitorProfile>;
}

export interface CompetitorSource {
  readonly source_id: string;
  readonly version_id?: string;
  readonly competitor_id: string | null;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly source_uri: string;
  readonly source_type: string;
  readonly purpose: string;
  readonly legal_basis_ref: string;
  readonly retention_expires_at: string;
  readonly data_classification: DataClassification;
  readonly evidence_refs?: ReadonlyArray<string>;
  readonly notes?: string | null;
  readonly subject_resolved?: boolean;
  readonly review_state?: SourceReviewState;
  readonly reviewed_by?: string | null;
  readonly reviewed_at?: string | null;
  readonly quarantine_reason?: string | null;
  readonly actor_id?: string | null;
  readonly created_at: string;
  readonly updated_at?: string | null;
}

export interface CompetitorSourceListResponse {
  readonly items: ReadonlyArray<CompetitorSource>;
}

export interface CompleteUploadResponse {
  readonly session: UploadSessionResponse;
  readonly document: SourceDocument;
}

export interface ComponentHealth {
  readonly name: string;
  readonly status: "UP" | "DOWN" | "DEGRADED" | "DISABLED";
  readonly detail?: string | null;
}

export interface ContractOnlyCommand {
  readonly reason_code?: string | null;
  readonly payload?: Record<string, unknown>;
}

export interface ContractOnlyResource {
  readonly contract_only?: boolean;
  readonly operation_id: string;
  readonly owner: string;
  readonly schema_status: string;
}

export interface CreateCompetitorRequest {
  readonly legal_name: string;
  readonly canonical_subject_key: string;
  readonly aliases?: ReadonlyArray<string>;
}

export interface CreateCompetitorSourceRequest {
  readonly source_uri: string;
  readonly source_type: string;
  readonly purpose: string;
  readonly legal_basis_ref: string;
  readonly retention_expires_at: string;
  readonly data_classification: DataClassification;
  readonly evidence_refs: ReadonlyArray<string>;
  readonly notes?: string | null;
}

export interface CreateMarketPriorRequest {
  readonly evidence_refs: ReadonlyArray<string>;
  readonly purpose: string;
  readonly legal_basis_ref: string;
  readonly valid_from: string;
  readonly expires_at: string;
  readonly distribution: Record<string, number>;
}

export interface CreateParseJobRequest {
  readonly document_id: string;
}

export interface CreateRiskAcceptanceRequest {
  readonly risk: string;
  readonly metric: string;
  readonly acceptance_scope: string;
  readonly rationale: string;
  readonly independent_approver_id: string;
  readonly valid_from: string;
  readonly valid_until: string;
}

export interface CreateSubjectDeduplicationRunRequest {
  readonly subject_keys: ReadonlyArray<string>;
}

export interface CreateUnknownEntrantProfileRequest {
  readonly excluded_subject_keys: ReadonlyArray<string>;
  readonly count_distribution: Record<string, number>;
  readonly evidence_refs: ReadonlyArray<string>;
  readonly expires_at: string;
}

export interface CreateUploadSessionRequest {
  readonly filename: string;
  readonly file_size_bytes: number;
  readonly declared_sha256: string;
  readonly content_type?: string;
  readonly kind?: DocumentKind;
  readonly chunk_size_bytes?: number;
}

export type CredentialUsageScope = "TEST_ONLY" | "BUSINESS_AND_DELETION" | "DELETION_ONLY" | "NONE";

export type DataClassification = "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "PERSONAL" | "SENSITIVE_PERSONAL";

export interface DatasetListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<DatasetSnapshotVersion>;
}

export interface DatasetSnapshotCreate {
  readonly name: string;
  readonly purpose: string;
  readonly source_asset_ids: ReadonlyArray<string>;
  readonly row_count: number;
  readonly content_hash: string;
  readonly observed_from?: string | null;
  readonly observed_until?: string | null;
}

export interface DatasetSnapshotVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly state: biaice__modules__model_governance__domain__models__PublicationState;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly dataset_id: string;
  readonly name: string;
  readonly purpose: string;
  readonly source_asset_ids: ReadonlyArray<string>;
  readonly row_count: number;
  readonly content_hash: string;
  readonly observed_from?: string | null;
  readonly observed_until?: string | null;
}

export type DeploymentState = "DRAFT" | "ACTIVE" | "SUPERSEDED" | "ROLLED_BACK";

export interface DerivedAsset {
  readonly asset_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly source_document_id: string;
  readonly source_document_version_id?: string | null;
  readonly parse_job_id?: string | null;
  readonly kind: DerivedAssetKind;
  readonly name: string;
  readonly description?: string | null;
  readonly storage_key: string;
  readonly storage_locator_hash: string;
  readonly size_bytes?: number | null;
  readonly content_hash?: string | null;
  readonly mime_type?: string | null;
  readonly page_number?: number | null;
  readonly fragment_ref: string;
  readonly created_at: string;
}

export type DerivedAssetKind = "OCR_TEXT" | "PAGE_IMAGE" | "PAGE_SLICE" | "EMBEDDING" | "INDEX" | "EXTRACTED_CONTENT" | "CACHE" | "PROMPT" | "MODEL_RESPONSE" | "EXPORT" | "BACKUP";

export interface DerivedAssetListResponse {
  readonly items: ReadonlyArray<DerivedAsset>;
}

export interface DetachDocumentLinkRequest {
  readonly link_id: string;
}

export type DocumentKind = "TENDER" | "COMPANY" | "COMPETITOR" | "MARKET";

export interface DocumentLink {
  readonly link_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly source_document_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly relation: DocumentLinkRelation;
  readonly priority?: number;
  readonly conflict_state?: DocumentLinkConflictState;
  readonly confirmation_reason?: string | null;
  readonly confirmed_by?: string | null;
  readonly created_by: string;
  readonly created_at: string;
  readonly detached_at?: string | null;
}

export type DocumentLinkConflictState = "NONE" | "OPEN" | "RESOLVED";

export type DocumentLinkRelation = "INHERITED" | "OVERRIDE";

export interface DocumentListResponse {
  readonly items: ReadonlyArray<SourceDocument>;
}

export type DocumentMimeCategory = "PDF" | "DOCX" | "XLSX" | "IMAGE" | "ARCHIVE" | "UNKNOWN" | "BLOCKED";

export type DocumentStatus = "QUARANTINED" | "SCAN_PASSED" | "SCAN_FAILED" | "UNDER_REVIEW" | "RELEASED" | "ARCHIVED" | "DELETED";

export type DriftStatus = "NO_DRIFT" | "WATCH" | "BREACH";

export interface EvaluationMetricDefinition {
  readonly code: string;
  readonly direction: MetricDirection;
  readonly threshold?: number | null;
  readonly target_value?: number | null;
}

export interface EvaluationProtocolCreate {
  readonly name: string;
  readonly dataset_id: string;
  readonly metrics: ReadonlyArray<EvaluationMetricDefinition>;
  readonly absolute_tolerance: number;
  readonly relative_tolerance: number;
  readonly aggregation_protocol: string;
  readonly cluster_unit: "DECISION_UNIT" | "PROJECT" | "BUYER";
}

export interface EvaluationProtocolListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<EvaluationProtocolVersion>;
}

export interface EvaluationProtocolVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly state: biaice__modules__model_governance__domain__models__PublicationState;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly evaluation_protocol_id: string;
  readonly name: string;
  readonly dataset_id: string;
  readonly metrics: ReadonlyArray<EvaluationMetricDefinition>;
  readonly absolute_tolerance: number;
  readonly relative_tolerance: number;
  readonly aggregation_protocol: string;
  readonly cluster_unit: "DECISION_UNIT" | "PROJECT" | "BUYER";
}

export type EvidenceStatus = "PASS" | "FAIL" | "UNKNOWN";

export type FeatureDataType = "STRING" | "INTEGER" | "FLOAT" | "BOOLEAN" | "CATEGORY" | "DATETIME";

export interface FeatureDefinition {
  readonly name: string;
  readonly data_type: FeatureDataType;
  readonly nullable?: boolean;
  readonly description?: string | null;
  readonly allowed_values?: ReadonlyArray<string>;
}

export interface FeatureSchemaCreate {
  readonly name: string;
  readonly features: ReadonlyArray<FeatureDefinition>;
  readonly schema_hash: string;
}

export interface FeatureSchemaListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<FeatureSchemaVersion>;
}

export interface FeatureSchemaVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly state: biaice__modules__model_governance__domain__models__PublicationState;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly feature_schema_id: string;
  readonly name: string;
  readonly features: ReadonlyArray<FeatureDefinition>;
  readonly schema_hash: string;
}

export interface FieldProblem {
  readonly field: string;
  readonly message: string;
  readonly error_type?: string | null;
}

export interface GateAssessment {
  readonly assessment_id: string;
  readonly gate_name: GateName;
  readonly status: GateStatus;
  readonly validity: GateValidity;
  readonly assessed_at: string;
  readonly expires_at: string;
  readonly responsible_party: string;
  readonly evidence: ReadonlyArray<GateEvidence>;
  readonly evidence_hash: string;
  readonly waiver_policy?: WaiverPolicy;
  readonly reason_codes?: ReadonlyArray<string>;
}

export interface GateAssessmentRequest {
  readonly reason_code: string;
}

export interface GateEvidence {
  readonly evidence_key: string;
  readonly status: EvidenceStatus;
  readonly checked_at: string;
  readonly checker: string;
  readonly evidence_hash: string;
  readonly expires_at: string;
}

export interface GateListResponse {
  readonly items: ReadonlyArray<GateAssessment>;
  readonly next_cursor?: string | null;
}

export type GateName = "REAL_DATA_MODE" | "BYOK_SECRET_GATE";

export type GateStatus = "PASS" | "FAIL" | "UNKNOWN";

export type GateValidity = "CURRENT" | "STALE";

export interface GateWaiverRequest {
  readonly reason_code: string;
  readonly compensation_control: string;
  readonly expires_at: string;
}

export interface HealthResponse {
  readonly status: "UP" | "DOWN" | "DEGRADED";
  readonly ready: boolean;
  readonly mode: "SYNTHETIC_ONLY" | "REAL_DATA";
  readonly checked_at: string;
  readonly version: string;
  readonly components: ReadonlyArray<ComponentHealth>;
}

export type IncidentSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IncidentState = "OPEN" | "CONTAINED" | "RESOLVED";

export interface InheritDocumentLinkRequest {
  readonly document_id: string;
  readonly decision_unit_id: string;
  readonly reason?: string | null;
}

export type JobState = "PENDING" | "QUEUED" | "RUNNING" | "CANCELLATION_REQUESTED" | "CANCELLED" | "SUCCEEDED" | "FAILED_RETRYABLE" | "FAILED_TERMINAL";

export interface JobView {
  readonly job_id: string;
  readonly job_type: string;
  readonly queue_name: string;
  readonly state: JobState;
  readonly progress_percent?: number | null;
  readonly attempt: number;
  readonly max_attempts: number;
  readonly created_at: string;
  readonly updated_at: string;
  readonly error_code?: string | null;
  readonly recoverable?: boolean;
  readonly status_url: string;
  readonly events_url: string;
}

export interface ManualOverrideRequest {
  readonly target_type: string;
  readonly target_id: string;
  readonly reason_code: string;
  readonly before_hash: string;
  readonly after_hash: string;
  readonly expires_at: string;
}

export interface MarketActionCommand {
  readonly reason_code?: string | null;
  readonly comment?: string | null;
  readonly target_state?: string | null;
  readonly effective_at?: string | null;
  readonly correlation_id?: string | null;
}

export interface MarketPriorListResponse {
  readonly items: ReadonlyArray<MarketPriorVersion>;
}

export interface MarketPriorVersion {
  readonly market_prior_id: string;
  readonly version_id?: string;
  readonly decision_unit_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly evidence_refs: ReadonlyArray<string>;
  readonly purpose: string;
  readonly legal_basis_ref: string;
  readonly valid_from: string;
  readonly expires_at: string;
  readonly state?: biaice__modules__market__domain__models__PublicationState;
  readonly distribution: Record<string, number>;
  readonly reviewed_by?: string | null;
  readonly reviewed_at?: string | null;
  readonly actor_id?: string | null;
  readonly created_at: string;
  readonly updated_at?: string | null;
  readonly published_at?: string | null;
}

export interface MarketResourceCommand {
  readonly subject_scope?: string | null;
  readonly justification_ref?: string | null;
  readonly legal_basis_ref?: string | null;
  readonly notice_ref?: string | null;
  readonly policy_ref?: string | null;
  readonly source_ref?: string | null;
  readonly provider_ref?: string | null;
  readonly evidence_refs?: ReadonlyArray<string> | null;
  readonly purpose?: string | null;
  readonly region?: string | null;
  readonly retention_days?: number | null;
  readonly delete_plan?: string | null;
  readonly risk_level?: string | null;
  readonly reviewer?: string | null;
  readonly description?: string | null;
}

export interface MarketResourcePage {
  readonly items?: ReadonlyArray<MarketResourceRecord>;
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
}

export interface MarketResourceRecord {
  readonly resource_id: string;
  readonly resource_type: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly state: string;
  readonly state_version: number;
  readonly payload: Record<string, unknown>;
  readonly status_reason?: string | null;
  readonly created_at: string;
  readonly created_by: string;
  readonly updated_at: string;
  readonly updated_by: string;
}

export type MarketResourceState = "APPROVED" | "ARCHIVED" | "CLOSED" | "COMPLETED" | "CONTAINED" | "CURRENT" | "DRAFT" | "EXPIRED" | "FROZEN" | "IDENTITY_VERIFIED" | "IN_PROGRESS" | "NOT_REQUIRED" | "OPEN" | "PUBLISHED" | "READY_TO_COMPLETE" | "RECEIVED" | "RECORDED" | "REJECTED" | "REMEDIATING" | "RESOLVED" | "REVOKED" | "TRIAGED" | "WAITING_FOR_INFORMATION";

export interface MeResponse {
  readonly subject_id: string;
  readonly username: string;
  readonly display_name: string | null;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly roles: ReadonlyArray<string>;
  readonly permissions: ReadonlyArray<string>;
  readonly mfa_verified: boolean;
  readonly authenticated_at: string;
}

export type MetricDirection = "MINIMIZE" | "MAXIMIZE" | "TARGET";

export interface ModelApprovalCreate {
  readonly model_artifact_id: string;
  readonly evaluation_protocol_id: string;
  readonly calibration_artifact_id?: string | null;
  readonly intended_purpose: string;
  readonly evidence_hash: string;
  readonly expires_at?: string | null;
}

export interface ModelApprovalDecision {
  readonly decision: "APPROVED" | "REJECTED";
  readonly rationale: string;
}

export interface ModelApprovalVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly model_approval_id: string;
  readonly model_artifact_id: string;
  readonly evaluation_protocol_id: string;
  readonly calibration_artifact_id?: string | null;
  readonly intended_purpose: string;
  readonly evidence_hash: string;
  readonly state: ApprovalState;
  readonly expires_at?: string | null;
  readonly decided_at?: string | null;
  readonly decided_by?: string | null;
  readonly decision_rationale?: string | null;
}

export interface ModelArtifactCreate {
  readonly name: string;
  readonly feature_schema_id: string;
  readonly catalog_id: string;
  readonly catalog_hash: string;
  readonly provider_id: string;
  readonly provider_model_id: string;
  readonly adapter_version: string;
  readonly api_version?: string | null;
  readonly code_or_image_digest: string;
  readonly prompt_template_id: string;
  readonly prompt_template_hash: string;
  readonly parameter_schema_hash: string;
  readonly dependency_lock_hash: string;
  readonly evaluation_evidence_hash: string;
  readonly randomness_protocol: string;
  readonly numeric_protocol: string;
}

export interface ModelArtifactListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<ModelArtifactVersion>;
}

export interface ModelArtifactVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly state: biaice__modules__model_governance__domain__models__PublicationState;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly model_artifact_id: string;
  readonly name: string;
  readonly feature_schema_id: string;
  readonly catalog_id: string;
  readonly catalog_hash: string;
  readonly provider_id: string;
  readonly provider_model_id: string;
  readonly adapter_version: string;
  readonly api_version?: string | null;
  readonly code_or_image_digest: string;
  readonly prompt_template_id: string;
  readonly prompt_template_hash: string;
  readonly parameter_schema_hash: string;
  readonly dependency_lock_hash: string;
  readonly evaluation_evidence_hash: string;
  readonly randomness_protocol: string;
  readonly numeric_protocol: string;
}

export interface ModelDeploymentCreate {
  readonly model_artifact_id: string;
  readonly model_approval_id: string;
  readonly provider_configuration_id: string;
  readonly deployment_slot: string;
  readonly intended_purpose: string;
}

export interface ModelDeploymentRollback {
  readonly reason: string;
  readonly evidence_hash: string;
  readonly model_incident_id?: string | null;
}

export interface ModelDeploymentVersion {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly model_deployment_id: string;
  readonly model_artifact_id: string;
  readonly model_approval_id: string;
  readonly provider_configuration_id: string;
  readonly deployment_slot: string;
  readonly intended_purpose: string;
  readonly state: DeploymentState;
  readonly supersedes_deployment_id?: string | null;
  readonly activated_at?: string | null;
  readonly activated_by?: string | null;
  readonly deactivated_at?: string | null;
  readonly deactivated_by?: string | null;
}

export interface ModelIncidentCreate {
  readonly model_deployment_id: string;
  readonly monitoring_snapshot_id?: string | null;
  readonly severity: IncidentSeverity;
  readonly summary: string;
  readonly detected_at: string;
  readonly evidence_hash: string;
}

export interface ModelIncidentEvent {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly model_incident_id: string;
  readonly model_deployment_id: string;
  readonly monitoring_snapshot_id?: string | null;
  readonly severity: IncidentSeverity;
  readonly state: IncidentState;
  readonly summary: string;
  readonly detected_at: string;
  readonly evidence_hash: string;
}

export interface ModelIncidentListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<ModelIncidentEvent>;
}

export interface ModelMonitoringSnapshot {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly monitoring_snapshot_id: string;
  readonly model_deployment_id: string;
  readonly evaluation_protocol_id: string;
  readonly window_start: string;
  readonly window_end: string;
  readonly sample_count: number;
  readonly metric_values: Record<string, number>;
  readonly drift_status: DriftStatus;
  readonly evidence_hash: string;
}

export interface MonitoringSnapshotCreate {
  readonly model_deployment_id: string;
  readonly evaluation_protocol_id: string;
  readonly window_start: string;
  readonly window_end: string;
  readonly sample_count: number;
  readonly metric_values: Record<string, number>;
  readonly drift_status: DriftStatus;
  readonly evidence_hash: string;
}

export interface MonitoringSnapshotListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<ModelMonitoringSnapshot>;
}

export interface OverrideDocumentLinkRequest {
  readonly document_id: string;
  readonly decision_unit_id: string;
  readonly reason: string;
  readonly priority?: number;
}

export interface ParseJobResponse {
  readonly parse_job_id: string;
  readonly document_id: string;
  readonly status: string;
  readonly stage: string | null;
  readonly progress_percent: number;
  readonly retryable: string | null;
  readonly failure_reason_code: string | null;
  readonly failure_detail: string | null;
  readonly attempt: number;
  readonly max_attempts: number;
  readonly derived_asset_ids: ReadonlyArray<string>;
  readonly created_at: string;
  readonly started_at: string | null;
  readonly completed_at: string | null;
}

export interface ProblemDetails {
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly detail: string;
  readonly instance?: string | null;
  readonly code: string;
  readonly request_id: string;
  readonly errors?: ReadonlyArray<FieldProblem>;
  readonly recoverable?: boolean;
  readonly remediation?: string | null;
}

export interface ProviderActionCommand {
  readonly reason_code: string;
}

export type ProviderActivationState = "INACTIVE" | "VERIFIED" | "ACTIVE" | "SUSPENDED" | "REVOKED";

export interface ProviderCatalogCreate {
  readonly entries: ReadonlyArray<ProviderCatalogEntryCreate>;
  readonly reason_code: string;
}

export interface ProviderCatalogDecision {
  readonly reason_code: string;
  readonly approval_evidence_hash: string;
}

export interface ProviderCatalogEntryCreate {
  readonly provider_id: string;
  readonly provider_legal_name: string;
  readonly provider_model_id: string;
  readonly display_name: string;
  readonly api_host: string;
  readonly adapter_id: string;
  readonly capabilities: ReadonlyArray<string>;
  readonly regions: ReadonlyArray<string>;
  readonly allowed_purposes: ReadonlyArray<string>;
  readonly max_input_tokens: number;
  readonly redaction_policy_summary: string;
  readonly training_use?: "DISABLED";
  readonly retention_days: number;
}

export interface ProviderCatalogPublicEntry {
  readonly provider_id: string;
  readonly provider_legal_name: string;
  readonly provider_model_id: string;
  readonly display_name: string;
  readonly capabilities: ReadonlyArray<string>;
  readonly regions: ReadonlyArray<string>;
  readonly allowed_purposes: ReadonlyArray<string>;
  readonly max_input_tokens: number;
  readonly redaction_policy_summary: string;
  readonly training_use: "DISABLED";
  readonly retention_days: number;
}

export type ProviderCatalogState = "DRAFT" | "PUBLISHED" | "REVOKED";

export interface ProviderCatalogVersion {
  readonly catalog_id: string;
  readonly version_number: number;
  readonly state: ProviderCatalogState;
  readonly catalog_hash: string;
  readonly entries: ReadonlyArray<ProviderCatalogEntryCreate>;
  readonly created_at: string;
  readonly created_by: string;
  readonly reason_code: string;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly approval_evidence_hash?: string | null;
  readonly revoked_at?: string | null;
  readonly revoked_by?: string | null;
  readonly revocation_reason?: string | null;
}

export interface ProviderConfigurationCreate {
  readonly catalog_id: string;
  readonly catalog_hash: string;
  readonly provider_id: string;
  readonly provider_model_id: string;
  readonly purpose: string;
  readonly monthly_budget_minor: number;
  readonly currency: string;
  readonly timeout_seconds: number;
  readonly retention_days: number;
  readonly legal_basis_evidence_id: string;
  readonly provider_policy_id: string;
  readonly pia_record_id: string;
  readonly cross_border_assessment_id: string;
}

export interface ProviderConfigurationPage {
  readonly items: ReadonlyArray<AIProviderConfiguration>;
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
}

export interface ProviderConfigurationSuccessorCreate {
  readonly rotation_mode: ProviderRotationMode;
  readonly reason_code: string;
}

export interface ProviderConfigurationUpdate {
  readonly purpose?: string | null;
  readonly monthly_budget_minor?: number | null;
  readonly currency?: string | null;
  readonly timeout_seconds?: number | null;
  readonly retention_days?: number | null;
  readonly legal_basis_evidence_id?: string | null;
  readonly provider_policy_id?: string | null;
  readonly pia_record_id?: string | null;
  readonly cross_border_assessment_id?: string | null;
}

export interface ProviderConnectionTestResult {
  readonly invocation_id: string;
  readonly reachable: boolean;
  readonly authenticated: boolean;
  readonly model_available: boolean;
  readonly rate_limited: boolean;
  readonly provider_health: ProviderHealth;
  readonly stable_error_code?: string | null;
  readonly tested_at: string;
}

export interface ProviderCredentialMetadata {
  readonly credential_reference_id: string;
  readonly credential_version: number;
  readonly fingerprint: string;
  readonly last_four: string;
  readonly created_at: string;
  readonly expires_at?: string | null;
}

export interface ProviderCredentialReceipt {
  readonly credential_reference_id: string;
  readonly credential_version: number;
  readonly fingerprint: string;
  readonly last_four: string;
  readonly created_at: string;
  readonly expires_at?: string | null;
  readonly credential_state: ProviderCredentialState;
  readonly credential_usage_scope: CredentialUsageScope;
}

export type ProviderCredentialState = "MISSING" | "UNVERIFIED" | "VALID" | "INVALID" | "EXPIRED" | "REVOKED";

export interface ProviderCredentialWrite {
  readonly api_key: string;
}

export interface ProviderDeletionAccepted {
  readonly job_id: string;
  readonly state?: "QUEUED";
  readonly status_url: string;
  readonly credential_state: ProviderCredentialState;
  readonly credential_usage_scope: CredentialUsageScope;
}

export type ProviderHealth = "UNKNOWN" | "HEALTHY" | "DEGRADED" | "UNAVAILABLE";

export interface ProviderInvocationPage {
  readonly items: ReadonlyArray<ProviderInvocationRecord>;
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
}

export interface ProviderInvocationRecord {
  readonly invocation_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly config_id: string;
  readonly provider_id: string;
  readonly provider_model_id: string;
  readonly purpose: "CONNECTION_TEST";
  readonly state: ProviderInvocationState;
  readonly attempt: number;
  readonly started_at: string;
  readonly completed_at: string;
  readonly request_hash: string;
  readonly response_hash?: string | null;
  readonly cost_minor: number;
  readonly currency: string;
  readonly stable_error_code?: string | null;
  readonly derived_asset_refs?: ReadonlyArray<string>;
}

export type ProviderInvocationState = "SUCCEEDED" | "FAILED" | "BLOCKED" | "TIMED_OUT";

export type ProviderRotationMode = "PLANNED" | "COMPROMISE";

export type ProviderValidity = "CURRENT" | "STALE" | "INVALIDATED";

export interface PublishedProviderCatalog {
  readonly catalog_id?: string | null;
  readonly catalog_hash?: string | null;
  readonly published_at?: string | null;
  readonly items?: ReadonlyArray<ProviderCatalogPublicEntry>;
}

export interface QuarantineCompetitorSourceRequest {
  readonly reason: string;
}

export type ReplicaKind = "DATABASE" | "OBJECT_STORAGE" | "SEARCH_INDEX" | "VECTOR_INDEX" | "CACHE" | "TEMPORARY_FILE" | "PROVIDER_EXTERNAL" | "BACKUP" | "AUDIT_DERIVED";

export interface ReplicaListResponse {
  readonly items: ReadonlyArray<ReplicaLocation>;
}

export interface ReplicaLocation {
  readonly replica_id: string;
  readonly target: ScopedObjectRef;
  readonly kind: ReplicaKind;
  readonly adapter_name: string;
  readonly adapter_owner: AdapterOwner;
  readonly locator_hash: string;
  readonly required_for_completion?: boolean;
  readonly deletion_sla_seconds: number;
  readonly retention_expires_at?: string | null;
}

export interface ResolveConflictDocumentLinkRequest {
  readonly link_id: string;
  readonly chosen_document_id: string;
  readonly reason: string;
}

export interface ReviewCompetitorSourceRequest {
  readonly resolved_competitor_id?: string | null;
  readonly notes?: string | null;
}

export interface RevokeRiskAcceptanceRequest {
  readonly revocation_reason: string;
}

export interface RiskAcceptance {
  readonly risk_acceptance_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly state: RiskAcceptanceState;
  readonly validity: RiskAcceptanceValidity;
  readonly risk: string;
  readonly metric: string;
  readonly acceptance_scope: string;
  readonly rationale: string;
  readonly independent_approver_id: string;
  readonly valid_from: string;
  readonly valid_until: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly accepted_at: string;
  readonly accepted_by: string;
  readonly revoked_at?: string | null;
  readonly revoked_by?: string | null;
  readonly revocation_reason?: string | null;
}

export interface RiskAcceptanceListResponse {
  readonly items: ReadonlyArray<RiskAcceptance>;
}

export type RiskAcceptanceState = "ACTIVE" | "REVOKED" | "EXPIRED";

export type RiskAcceptanceValidity = "CURRENT" | "STALE" | "EXPIRED" | "INVALIDATED";

export interface RollbackEvent {
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly rollback_event_id: string;
  readonly model_deployment_id: string;
  readonly from_model_artifact_id: string;
  readonly to_model_artifact_id?: string | null;
  readonly model_incident_id?: string | null;
  readonly reason: string;
  readonly evidence_hash: string;
}

export interface RollbackEventCreate {
  readonly model_deployment_id: string;
  readonly from_model_artifact_id: string;
  readonly to_model_artifact_id?: string | null;
  readonly model_incident_id?: string | null;
  readonly reason: string;
  readonly evidence_hash: string;
}

export interface RollbackEventListResponse {
  readonly next_cursor?: string | null;
  readonly has_more?: boolean;
  readonly items: ReadonlyArray<RollbackEvent>;
}

export type ScanResult = "CLEAN" | "INFECTED" | "ERROR";

export interface ScopedObjectRef {
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id?: string | null;
  readonly object_type: string;
  readonly object_id: string;
  readonly version_id?: string | null;
}

export interface SourceDocument {
  readonly document_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id?: string | null;
  readonly kind: DocumentKind;
  readonly name: string;
  readonly storage_key: string;
  readonly storage_locator_hash: string;
  readonly size_bytes: number;
  readonly content_hash: string;
  readonly declared_content_type: string;
  readonly sniffed_content_type: string;
  readonly mime_category: DocumentMimeCategory;
  readonly scan_result: ScanResult;
  readonly scan_signature_version?: string | null;
  readonly scan_details?: string | null;
  readonly status: DocumentStatus;
  readonly quarantined_at?: string | null;
  readonly scan_completed_at?: string | null;
  readonly released_at?: string | null;
  readonly uploaded_by: string;
  readonly uploaded_at: string;
  readonly reviewed_by?: string | null;
  readonly reviewed_at?: string | null;
  readonly released_by?: string | null;
  readonly upload_session_id: string;
  readonly source_filename?: string | null;
}

export type SourceReviewState = "DRAFT" | "REVIEWED" | "QUARANTINED" | "EXPIRED";

export interface SubjectDeduplicationRun {
  readonly run_id: string;
  readonly decision_unit_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly state?: SubjectDeduplicationState;
  readonly input_subject_keys: ReadonlyArray<string>;
  readonly canonical_subject_keys: ReadonlyArray<string>;
  readonly duplicate_groups?: Record<string, ReadonlyArray<string>>;
  readonly named_subject_matches?: ReadonlyArray<string>;
  readonly actor_id: string;
  readonly created_at: string;
  readonly completed_at: string;
}

export type SubjectDeduplicationState = "SUCCEEDED";

export interface UnknownEntrantProfileListResponse {
  readonly items: ReadonlyArray<UnknownEntrantProfileVersion>;
}

export interface UnknownEntrantProfileVersion {
  readonly profile_id: string;
  readonly version_id?: string;
  readonly decision_unit_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly excluded_subject_keys: ReadonlyArray<string>;
  readonly count_distribution: Record<string, number>;
  readonly evidence_refs: ReadonlyArray<string>;
  readonly expires_at: string;
  readonly state?: biaice__modules__market__domain__models__PublicationState;
  readonly actor_id?: string | null;
  readonly created_at: string;
  readonly updated_at?: string | null;
  readonly published_at?: string | null;
}

export interface UpdateCompetitorDraftRequest {
  readonly legal_name?: string | null;
  readonly canonical_subject_key?: string | null;
  readonly aliases?: ReadonlyArray<string> | null;
}

export interface UploadChunkResponse {
  readonly part_number: number;
  readonly offset: number;
  readonly size_bytes: number;
  readonly expected_sha256: string;
  readonly received_sha256: string | null;
  readonly received_at: string | null;
}

export interface UploadSessionResponse {
  readonly session_id: string;
  readonly status: string;
  readonly kind: DocumentKind;
  readonly filename: string;
  readonly file_size_bytes: number;
  readonly content_type: string;
  readonly mime_category: string;
  readonly declared_sha256: string;
  readonly chunk_size_bytes: number;
  readonly total_parts: number;
  readonly received_parts: ReadonlyArray<UploadChunkResponse>;
  readonly next_action: string;
  readonly missing_part_numbers: ReadonlyArray<number>;
  readonly document_id: string | null;
  readonly expires_at: string;
  readonly created_at: string;
  readonly completed_at: string | null;
}

export type WaiverPolicy = "PROHIBITED" | "ALLOWED";

export type biaice__modules__market__domain__models__PublicationState = "DRAFT" | "REVIEWED" | "PUBLISHED" | "EXPIRED" | "REVOKED" | "QUARANTINED";

export type biaice__modules__model_governance__domain__models__PublicationState = "DRAFT" | "PUBLISHED";
