// Generated from openapi.generated.json. Do not edit.
/* eslint-disable */

export type BlockingStage = "COMPUTE" | "FREEZE" | "APPROVAL" | "AUTHORIZATION" | "SUBMISSION";

export interface CommercialPolicy {
  readonly policy_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly profit_floor: string;
  readonly cashflow_constraint: string;
  readonly capacity_constraint: string;
  readonly risk_threshold: string;
  readonly coverage_ratio: string;
  readonly min_award_quality: string;
  readonly objective_weights?: Record<string, string>;
  readonly merge_tolerance: string;
  readonly exception_authority: string;
  readonly lifecycle_state: LifecycleState;
  readonly review_state: ReviewState;
  readonly validity_state: ValidityState;
  readonly retention_state?: RetentionState;
  readonly effective_from?: string | null;
  readonly effective_to?: string | null;
  readonly superseded_by_id?: string | null;
  readonly created_at: string;
  readonly created_by: string;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
}

export interface CompanyEvidence {
  readonly lifecycle_state: LifecycleState;
  readonly review_state: ReviewState;
  readonly validity_state: ValidityState;
  readonly retention_state?: RetentionState;
  readonly effective_from?: string | null;
  readonly effective_to?: string | null;
  readonly superseded_by_id?: string | null;
  readonly evidence_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly category: EvidenceCategory;
  readonly subject: string;
  readonly summary: string;
  readonly source: string;
  readonly source_document_id?: string | null;
  readonly fragment_ref?: string | null;
  readonly content_hash?: string | null;
  readonly valid_from: string;
  readonly valid_to: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly reviewed_at?: string | null;
  readonly reviewed_by?: string | null;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly revoked_at?: string | null;
  readonly revoked_by?: string | null;
  readonly revocation_reason?: string | null;
}

export interface CompanyResponseProfile {
  readonly lifecycle_state: LifecycleState;
  readonly review_state: ReviewState;
  readonly validity_state: ValidityState;
  readonly retention_state?: RetentionState;
  readonly effective_from?: string | null;
  readonly effective_to?: string | null;
  readonly superseded_by_id?: string | null;
  readonly profile_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly qualification_preparation: string;
  readonly technical_response: string;
  readonly service_response: string;
  readonly objective_non_price_inputs?: Record<string, string>;
  readonly subjective_variable_intervals?: Record<string, string>;
  readonly evidence_ids?: ReadonlyArray<string>;
  readonly valid_from: string;
  readonly valid_to: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
}

export interface ComponentHealth {
  readonly name: string;
  readonly status: "UP" | "DOWN" | "DEGRADED" | "DISABLED";
  readonly detail?: string | null;
}

export interface ConditionCommandRequest {
  readonly reason: string;
}

export interface ConditionListResponse {
  readonly items: ReadonlyArray<ConditionRequirement>;
}

export interface ConditionRequirement {
  readonly condition_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly title: string;
  readonly statement: string;
  readonly state: ConditionState;
  readonly owner_id: string;
  readonly independent_reviewer_id: string;
  readonly evidence_id?: string | null;
  readonly due_at: string;
  readonly blocking_stage: BlockingStage;
  readonly created_at: string;
  readonly created_by: string;
  readonly closed_at?: string | null;
  readonly closed_by?: string | null;
  readonly close_reason?: string | null;
}

export type ConditionState = "OPEN" | "SATISFIED" | "WAIVED" | "FAILED" | "EXPIRED";

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

export interface CostBaseline {
  readonly cost_baseline_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly currency: string;
  readonly tax_mode: TaxMode;
  readonly input_vat: Money-Output;
  readonly cycle: string;
  readonly delivery_cost: Money-Output;
  readonly post_award_cost: Money-Output;
  readonly bid_preparation_cost: Money-Output;
  readonly cashflow_in: Money-Output;
  readonly cashflow_out: Money-Output;
  readonly lifecycle_state: LifecycleState;
  readonly review_state: ReviewState;
  readonly validity_state: ValidityState;
  readonly retention_state?: RetentionState;
  readonly effective_from?: string | null;
  readonly effective_to?: string | null;
  readonly superseded_by_id?: string | null;
  readonly created_at: string;
  readonly created_by: string;
  readonly approved_at?: string | null;
  readonly approved_by?: string | null;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
  readonly exploration_only: boolean;
}

export interface CostListResponse {
  readonly items: ReadonlyArray<CostBaseline>;
}

export interface CreateConditionRequest {
  readonly title: string;
  readonly statement: string;
  readonly owner_id: string;
  readonly independent_reviewer_id: string;
  readonly evidence_id?: string | null;
  readonly due_at: string;
  readonly blocking_stage: BlockingStage;
}

export interface CreateCostRequest {
  readonly currency: string;
  readonly tax_mode: TaxMode;
  readonly input_vat: Money-Input;
  readonly cycle: string;
  readonly delivery_cost: Money-Input;
  readonly post_award_cost: Money-Input;
  readonly bid_preparation_cost: Money-Input;
  readonly cashflow_in: Money-Input;
  readonly cashflow_out: Money-Input;
}

export interface CreateEvidenceRequest {
  readonly category: EvidenceCategory;
  readonly subject: string;
  readonly summary: string;
  readonly source: string;
  readonly source_document_id?: string | null;
  readonly fragment_ref?: string | null;
  readonly valid_from: string;
  readonly valid_to: string;
}

export interface CreateMatchRequest {
  readonly requirement_id: string;
  readonly evidence_id?: string | null;
  readonly state?: MatchState;
  readonly rationale: string;
}

export interface CreatePolicyRequest {
  readonly profit_floor: string;
  readonly cashflow_constraint: string;
  readonly capacity_constraint: string;
  readonly risk_threshold: string;
  readonly coverage_ratio: string;
  readonly min_award_quality: string;
  readonly objective_weights?: Record<string, string>;
  readonly merge_tolerance: string;
  readonly exception_authority: string;
}

export interface CreateProfileRequest {
  readonly qualification_preparation: string;
  readonly technical_response: string;
  readonly service_response: string;
  readonly objective_non_price_inputs?: Record<string, string>;
  readonly subjective_variable_intervals?: Record<string, string>;
  readonly evidence_ids?: ReadonlyArray<string>;
  readonly valid_from: string;
  readonly valid_to: string;
}

export interface CreateRequirementRequest {
  readonly title: string;
  readonly statement: string;
  readonly mandatory?: boolean;
  readonly rule_clause_id?: string | null;
  readonly source_document_id?: string | null;
  readonly source_page?: string | null;
  readonly source_section?: string | null;
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

export type EvidenceCategory = "QUALIFICATION" | "CASE" | "PERSONNEL" | "TECHNICAL" | "SERVICE" | "COMMITMENT";

export interface EvidenceListResponse {
  readonly items: ReadonlyArray<CompanyEvidence>;
}

export interface EvidenceMatch {
  readonly match_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly requirement_id: string;
  readonly evidence_id?: string | null;
  readonly state: MatchState;
  readonly rationale: string;
  readonly original_etag?: string | null;
  readonly reviewed_at?: string | null;
  readonly reviewed_by?: string | null;
  readonly created_at: string;
  readonly created_by: string;
  readonly validity_state?: ValidityState;
}

export type EvidenceStatus = "PASS" | "FAIL" | "UNKNOWN";

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

export type LifecycleState = "DRAFT" | "PUBLISHED" | "ARCHIVED" | "DELETED";

export interface ManualOverrideRequest {
  readonly target_type: string;
  readonly target_id: string;
  readonly reason_code: string;
  readonly before_hash: string;
  readonly after_hash: string;
  readonly expires_at: string;
}

export interface MatchListResponse {
  readonly items: ReadonlyArray<EvidenceMatch>;
}

export type MatchState = "SATISFIED" | "PARTIAL" | "UNSATISFIED" | "UNKNOWN";

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

export interface Money-Input {
  readonly amount: number | string;
  readonly currency: string;
}

export interface Money-Output {
  readonly amount: string;
  readonly currency: string;
}

export interface PolicyListResponse {
  readonly items: ReadonlyArray<CommercialPolicy>;
}

export interface PrecheckAssessment {
  readonly precheck_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly decision: PrecheckDecision;
  readonly validity_state: ValidityState;
  readonly rules_available: boolean | null;
  readonly subject_qualification: MatchState;
  readonly substantive_response: MatchState;
  readonly evidence_coverage: MatchState;
  readonly deadline_closure: boolean | null;
  readonly unmapped_mandatory_count: number;
  readonly condition_ids?: ReadonlyArray<string>;
  readonly checks?: ReadonlyArray<PrecheckCheck>;
  readonly created_at: string;
  readonly created_by: string;
}

export interface PrecheckCheck {
  readonly code: string;
  readonly passed: boolean | null;
  readonly reason_code: string;
}

export type PrecheckDecision = "PASS" | "CONDITIONAL" | "BLOCKED" | "UNKNOWN";

export interface PrecheckListResponse {
  readonly items: ReadonlyArray<PrecheckAssessment>;
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

export interface ProfileListResponse {
  readonly items: ReadonlyArray<CompanyResponseProfile>;
}

export type ReadinessDecision = "READY" | "CONDITIONAL" | "NOT_READY" | "UNKNOWN";

export interface ReadinessItem {
  readonly code: string;
  readonly decision: ReadinessDecision;
  readonly reason_code: string;
  readonly commercial_not_procurement?: boolean;
}

export interface ReadinessListResponse {
  readonly items: ReadonlyArray<StrategyReadinessAssessment>;
}

export interface Requirement {
  readonly lifecycle_state: LifecycleState;
  readonly review_state: ReviewState;
  readonly validity_state: ValidityState;
  readonly retention_state?: RetentionState;
  readonly effective_from?: string | null;
  readonly effective_to?: string | null;
  readonly superseded_by_id?: string | null;
  readonly requirement_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly rule_clause_id?: string | null;
  readonly title: string;
  readonly statement: string;
  readonly mandatory: boolean;
  readonly source_document_id?: string | null;
  readonly source_page?: string | null;
  readonly source_section?: string | null;
  readonly etag: string;
  readonly created_at: string;
  readonly created_by: string;
  readonly published_at?: string | null;
  readonly published_by?: string | null;
}

export interface RequirementListResponse {
  readonly items: ReadonlyArray<Requirement>;
}

export type RetentionState = "RETAIN" | "DISPOSITION_DUE" | "DISPOSITION_RUNNING" | "DISPOSED";

export interface ReviewMatchRequest {
  readonly state: MatchState;
  readonly rationale: string;
}

export type ReviewState = "PENDING" | "APPROVED" | "NOT_REQUIRED" | "REJECTED" | "QUARANTINED";

export interface RevokeRequest {
  readonly reason: string;
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

export interface StrategyReadinessAssessment {
  readonly readiness_id: string;
  readonly version_id: string;
  readonly tenant_id: string;
  readonly data_domain_id: string;
  readonly project_id?: string | null;
  readonly decision_unit_id: string;
  readonly decision: ReadinessDecision;
  readonly validity_state: ValidityState;
  readonly items: ReadonlyArray<ReadinessItem>;
  readonly created_at: string;
  readonly created_by: string;
  readonly exploration_watermark: boolean;
}

export type TaxMode = "INCLUSIVE" | "EXCLUSIVE";

export interface UpdateRequirementRequest {
  readonly title: string;
  readonly statement: string;
  readonly mandatory?: boolean;
}

export type ValidityState = "CURRENT" | "STALE" | "INVALIDATED";

export type WaiverPolicy = "PROHIBITED" | "ALLOWED";
