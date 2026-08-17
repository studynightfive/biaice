// Generated from openapi.generated.json. Do not edit.
/* eslint-disable */

export type AdapterOwner = "MEMBER_1_GOVERNANCE" | "MEMBER_3_LOCAL_REPLICA" | "MEMBER_5_PROVIDER_REPLICA";

export interface AssessmentListResponse {
  readonly items: ReadonlyArray<ScenarioStrategyAssessment>;
}

export type AwardMode = "SINGLE" | "MULTI" | "NONE";

export interface BaselineListResponse {
  readonly items: ReadonlyArray<DecisionBaseline>;
}

export type BaselineState = "DRAFT" | "FROZEN" | "SUPERSEDED" | "INVALIDATED";

export interface BatchListResponse {
  readonly items: ReadonlyArray<SimulationBatch>;
}

export type BatchState = "PENDING" | "RUNNING" | "SUCCEEDED" | "INDETERMINATE" | "FAILED_RETRYABLE" | "FAILED_TERMINAL" | "CANCELLED";

export interface CandidateBlueprintRequest {
  readonly label: string;
  readonly parameters?: Record<string, unknown>;
  readonly expected_cost: string;
  readonly expected_margin: string;
}

export interface CandidateListResponse {
  readonly items: ReadonlyArray<SimulationCandidate>;
}

export interface CandidateSearchSpace {
  readonly search_space_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly baseline_version_id: string;
  readonly description: string;
  readonly state: SearchSpaceState;
  readonly dimension_axes: ReadonlyArray<string>;
  readonly candidate_count_lower_bound: number;
  readonly created_at: string;
  readonly created_by: string;
  readonly frozen_at: string | null;
  readonly frozen_by: string | null;
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

export interface CreateBatchRequest {
  readonly decision_unit_id: string;
  readonly baseline_id: string;
  readonly scenario_set_id: string;
  readonly award_mode: AwardMode;
  readonly policy_threshold: string;
}

export interface CreateOptimizationRunRequest {
  readonly objective_kind: ObjectiveKind;
  readonly award_mode: AwardMode;
  readonly policy_threshold: string;
  readonly blueprints: ReadonlyArray<CandidateBlueprintRequest>;
  readonly stress_axes: ReadonlyArray<StressAxis>;
  readonly stress_scenarios?: ReadonlyArray<StressScenarioRequest>;
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

export interface CreateScenarioSetRequest {
  readonly decision_unit_id: string;
  readonly baseline_id: string;
  readonly search_space_id: string;
  readonly evaluation_space_id?: string | null;
  readonly members: ReadonlyArray<ScenarioSetMemberRequest>;
  readonly stress_axes?: ReadonlyArray<string>;
}

export interface CreateSearchSpaceRequest {
  readonly decision_unit_id: string;
  readonly baseline_id: string;
  readonly description: string;
  readonly dimension_axes: ReadonlyArray<string>;
  readonly candidate_count_lower_bound: number;
}

export interface CreateUploadSessionRequest {
  readonly filename: string;
  readonly file_size_bytes: number;
  readonly declared_sha256: string;
  readonly content_type?: string;
  readonly kind?: DocumentKind;
  readonly chunk_size_bytes?: number;
}

export interface DecimalStr {
  readonly value: string;
}

export interface DecisionBaseline {
  readonly baseline_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly manifest: InputManifest;
  readonly state: BaselineState;
  readonly frozen_at: string | null;
  readonly frozen_by: string | null;
  readonly created_at: string;
  readonly created_by: string;
  readonly superseded_at?: string | null;
  readonly superseded_by?: string | null;
  readonly invalidated_at?: string | null;
  readonly invalidated_by?: string | null;
}

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

export interface EligibilityListResponse {
  readonly items: ReadonlyArray<RecommendationEligibility>;
}

export type EligibilityState = "ELIGIBLE" | "INELIGIBLE" | "INDETERMINATE";

export type EvidenceStatus = "PASS" | "FAIL" | "UNKNOWN";

export interface FieldProblem {
  readonly field: string;
  readonly message: string;
  readonly error_type?: string | null;
}

export interface FreezeBaselineRequest {
  readonly decision_unit_id: string;
  readonly manifest_items: ReadonlyArray<ManifestItemRequest>;
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

export interface InheritDocumentLinkRequest {
  readonly document_id: string;
  readonly decision_unit_id: string;
  readonly reason?: string | null;
}

export interface InputManifest {
  readonly manifest_id: string;
  readonly manifest_hash: string;
  readonly items: ReadonlyArray<ManifestItem>;
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

export interface ManifestItem {
  readonly item_id: string;
  readonly upstream_type: string;
  readonly upstream_id: string;
  readonly upstream_version_id: string;
  readonly upstream_content_hash: string;
  readonly dependency_type: string;
  readonly recorded_at: string;
}

export interface ManifestItemRequest {
  readonly item_id: string;
  readonly upstream_type: string;
  readonly upstream_id: string;
  readonly upstream_version_id: string;
  readonly upstream_content_hash: string;
  readonly dependency_type: string;
  readonly recorded_at: string;
}

export interface ManualOverrideRequest {
  readonly target_type: string;
  readonly target_id: string;
  readonly reason_code: string;
  readonly before_hash: string;
  readonly after_hash: string;
  readonly expires_at: string;
}

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

export interface MergeAssessment {
  readonly merge_id: string;
  readonly run_id: string;
  readonly plan_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly linkage: string;
  readonly tau_b: DecimalStr;
  readonly tau_m: DecimalStr;
  readonly accepted: boolean;
  readonly blocked_reason_code: string | null;
  readonly assessed_at: string;
}

export interface MergeAssessmentListResponse {
  readonly items: ReadonlyArray<MergeAssessment>;
}

export type ObjectiveKind = "COST_MIN" | "MARGIN_MAX" | "COVERAGE_MAX" | "RISK_MIN";

export interface OptimizationRun {
  readonly run_id: string;
  readonly batch_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly state: OptimizationState;
  readonly award_mode: AwardMode;
  readonly objective_kind: ObjectiveKind;
  readonly policy_threshold: DecimalStr;
  readonly progress_percent?: number;
  readonly requested_by: string;
  readonly created_at: string;
  readonly finalized_at: string | null;
  readonly invalidated_at: string | null;
  readonly invalidated_by?: string | null;
}

export interface OptimizationRunListResponse {
  readonly items: ReadonlyArray<OptimizationRun>;
}

export type OptimizationState = "DRAFT" | "RUNNING" | "SUCCEEDED" | "FAILED" | "INVALIDATED" | "FINALIZED";

export interface OutcomeListResponse {
  readonly items: ReadonlyArray<ScenarioOutcome>;
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

export type PlanState = "DRAFT" | "PUBLISHED" | "INVALIDATED";

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

export interface RecommendationEligibility {
  readonly eligibility_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly state: EligibilityState;
  readonly blocked_reason_codes?: ReadonlyArray<string>;
  readonly upstream_validity?: Record<string, ReviewValidity>;
  readonly baseline_version_id: string;
  readonly snapshot_version_id?: string | null;
  readonly assessed_at: string;
  readonly assessed_by: string;
}

export interface RecommendationEligibilityRequest {
  readonly baseline_id: string;
  readonly snapshot_id?: string | null;
  readonly precheck: ReviewValidity;
  readonly readiness: ReviewValidity;
  readonly static_validation: ReviewValidity;
  readonly scenario_assessment: ReviewValidity;
  readonly condition: ReviewValidity;
  readonly risk_acceptance: ReviewValidity;
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

export type ReviewValidity = "CURRENT" | "UNKNOWN" | "EXPIRED" | "INVALIDATED";

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

export type ScanResult = "CLEAN" | "INFECTED" | "ERROR";

export type ScenarioKind = "SEARCH" | "EVALUATION" | "STRESS";

export interface ScenarioOutcome {
  readonly outcome_id: string;
  readonly candidate_id: string;
  readonly scenario_id: string;
  readonly batch_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly feasible: boolean;
  readonly expected_payoff: DecimalStr;
  readonly p_win: DecimalStr;
  readonly evaluated_at: string;
  readonly review_validity: ReviewValidity;
  readonly detail?: string | null;
}

export interface ScenarioSet {
  readonly scenario_set_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly baseline_version_id: string;
  readonly search_space_version_id: string;
  readonly evaluation_space_version_id: string | null;
  readonly stress_axes: ReadonlyArray<StressAxis>;
  readonly state: ScenarioSetState;
  readonly members: ReadonlyArray<ScenarioSetMember>;
  readonly created_at: string;
  readonly created_by: string;
  readonly frozen_at: string | null;
  readonly frozen_by: string | null;
}

export interface ScenarioSetListResponse {
  readonly items: ReadonlyArray<ScenarioSet>;
}

export interface ScenarioSetMember {
  readonly scenario_id: string;
  readonly scenario_kind: ScenarioKind;
  readonly weight: DecimalStr;
  readonly label: string;
  readonly params?: Record<string, unknown>;
}

export interface ScenarioSetMemberRequest {
  readonly scenario_id: string;
  readonly scenario_kind: string;
  readonly weight: string;
  readonly label: string;
  readonly params?: Record<string, unknown>;
}

export type ScenarioSetState = "DRAFT" | "FROZEN" | "SUPERSEDED" | "INVALIDATED";

export interface ScenarioStrategyAssessment {
  readonly assessment_id: string;
  readonly candidate_id: string;
  readonly scenario_id: string;
  readonly batch_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly review_validity: ReviewValidity;
  readonly summary: string;
  readonly recommended: boolean;
  readonly assessed_at: string;
  readonly reason_code: string;
}

export interface ScopedObjectRef {
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id?: string | null;
  readonly object_type: string;
  readonly object_id: string;
  readonly version_id?: string | null;
}

export interface SearchSpaceListResponse {
  readonly items: ReadonlyArray<CandidateSearchSpace>;
}

export type SearchSpaceState = "DRAFT" | "FROZEN" | "SUPERSEDED" | "INVALIDATED";

export interface SimulationAssessmentSnapshot {
  readonly snapshot_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly state: SnapshotState;
  readonly watermark: string;
  readonly payload_hash: string;
  readonly payload: Record<string, unknown>;
  readonly created_at: string;
  readonly created_by: string;
  readonly locked_at?: string | null;
  readonly locked_by?: string | null;
}

export interface SimulationBatch {
  readonly batch_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly baseline_version_id: string;
  readonly scenario_set_version_id: string;
  readonly award_mode: AwardMode;
  readonly state: BatchState;
  readonly policy_threshold: DecimalStr;
  readonly candidate_count: number;
  readonly progress_percent?: number;
  readonly requested_by: string;
  readonly created_at: string;
  readonly last_updated_at: string;
  readonly job_id?: string | null;
  readonly failure_reason_code?: string | null;
}

export interface SimulationCandidate {
  readonly candidate_id: string;
  readonly batch_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly label: string;
  readonly parameters: Record<string, unknown>;
  readonly expected_cost: DecimalStr;
  readonly expected_margin: DecimalStr;
  readonly created_at: string;
}

export interface SnapshotDownloadResponse {
  readonly snapshot: SimulationAssessmentSnapshot;
}

export interface SnapshotListResponse {
  readonly items: ReadonlyArray<SimulationAssessmentSnapshot>;
}

export interface SnapshotRequest {
  readonly payload: Record<string, unknown>;
}

export type SnapshotState = "DRAFT" | "LOCKED";

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

export interface StaticCandidateValidation {
  readonly validation_id: string;
  readonly candidate_id: string;
  readonly batch_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly status: StaticValidationStatus;
  readonly rule_codes?: ReadonlyArray<string>;
  readonly assessed_at: string;
  readonly detail?: string | null;
}

export interface StaticValidationListResponse {
  readonly items: ReadonlyArray<StaticCandidateValidation>;
}

export type StaticValidationStatus = "PASS" | "FAIL" | "INDETERMINATE";

export interface StrategyPlan {
  readonly plan_id: string;
  readonly run_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly state: PlanState;
  readonly award_mode: AwardMode;
  readonly objective_kind: ObjectiveKind;
  readonly members: ReadonlyArray<StrategyPlanMember>;
  readonly p_minus: DecimalStr;
  readonly p_plus: DecimalStr;
  readonly coverage: DecimalStr;
  readonly created_at: string;
  readonly published_at: string | null;
  readonly invalidated_at: string | null;
  readonly invalidated_by?: string | null;
  readonly published_by?: string | null;
  readonly linked_run_version_id: string;
}

export interface StrategyPlanListResponse {
  readonly items: ReadonlyArray<StrategyPlan>;
}

export interface StrategyPlanMember {
  readonly candidate_id: string;
  readonly linkage?: string;
  readonly weight: DecimalStr;
}

export interface StressAssessmentListResponse {
  readonly items: ReadonlyArray<StressTestAssessment>;
}

export type StressAxis = "PRICE_BAND" | "TIMING" | "COMPLIANCE" | "PROVIDER_OUTAGE" | "UNIT_FAILURE";

export interface StressScenarioRequest {
  readonly axis: StressAxis;
  readonly feasible: boolean;
  readonly stress_weight: string;
  readonly detail: string;
}

export interface StressTestAssessment {
  readonly assessment_id: string;
  readonly run_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id: string | null;
  readonly decision_unit_id: string;
  readonly axis: StressAxis;
  readonly passed: boolean;
  readonly detail: string;
  readonly assessed_at: string;
  readonly stress_weight: DecimalStr;
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
