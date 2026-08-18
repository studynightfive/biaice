// Generated from openapi.generated.json. Do not edit.
/* eslint-disable */
import type * as Models from "./types";

export interface RequestOptions {
  readonly path?: Readonly<Record<string, string | number>>;
  readonly query?: Readonly<Record<string, string | number | boolean | undefined>>;
  readonly body?: unknown;
  readonly idempotencyKey?: string;
  readonly ifMatch?: string;
  readonly signal?: AbortSignal;
}

export class BiaiceProblem extends Error {
  constructor(readonly problem: Models.ProblemDetails) { super(problem.detail); }
}

export class BiaiceClient {
  constructor(private readonly baseUrl = "") {}
  async request<T>(method: string, template: string, options: RequestOptions = {}): Promise<T> {
    const path = template.replace(/\{([^}]+)\}/g, (_, key: string) => {
      const value = options.path?.[key];
      if (value === undefined) throw new Error(`Missing path parameter: ${key}`);
      return encodeURIComponent(String(value));
    });
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);
    for (const [key, value] of Object.entries(options.query ?? {})) if (value !== undefined) url.searchParams.set(key, String(value));
    const headers = new Headers({ Accept: "application/json, application/problem+json" });
    if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
    if (options.ifMatch) headers.set("If-Match", options.ifMatch);
    if (options.body !== undefined) headers.set("Content-Type", "application/json");
    // Tenant/data-domain headers are intentionally unsupported; scope comes from the server session.
    const response = await fetch(url, { method, credentials: "include", headers, body: options.body === undefined ? undefined : JSON.stringify(options.body), signal: options.signal });
    if (!response.ok) throw new BiaiceProblem(await response.json() as Models.ProblemDetails);
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  }
}

export async function list_ai_provider_catalog(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.PublishedProviderCatalog> {
  return client.request<Models.PublishedProviderCatalog>("GET", "/api/v1/ai-provider-catalog", options);
}

export async function list_ai_provider_configurations(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderConfigurationPage> {
  return client.request<Models.ProviderConfigurationPage>("GET", "/api/v1/ai-provider-configurations", options);
}

export async function create_ai_provider_configuration(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AIProviderConfiguration> {
  return client.request<Models.AIProviderConfiguration>("POST", "/api/v1/ai-provider-configurations", options);
}

export async function get_ai_provider_configuration(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AIProviderConfiguration> {
  return client.request<Models.AIProviderConfiguration>("GET", "/api/v1/ai-provider-configurations/{config_id}", options);
}

export async function update_ai_provider_configuration(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AIProviderConfiguration> {
  return client.request<Models.AIProviderConfiguration>("PATCH", "/api/v1/ai-provider-configurations/{config_id}", options);
}

export async function activate_ai_provider_configuration(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AIProviderConfiguration> {
  return client.request<Models.AIProviderConfiguration>("POST", "/api/v1/ai-provider-configurations/{config_id}/activate", options);
}

export async function revoke_ai_provider_credential(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderDeletionAccepted> {
  return client.request<Models.ProviderDeletionAccepted>("DELETE", "/api/v1/ai-provider-configurations/{config_id}/credential", options);
}

export async function set_ai_provider_credential(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderCredentialReceipt> {
  return client.request<Models.ProviderCredentialReceipt>("PUT", "/api/v1/ai-provider-configurations/{config_id}/credential", options);
}

export async function revoke_ai_provider_configuration(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderDeletionAccepted> {
  return client.request<Models.ProviderDeletionAccepted>("POST", "/api/v1/ai-provider-configurations/{config_id}/revoke", options);
}

export async function create_ai_provider_configuration_successor(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AIProviderConfiguration> {
  return client.request<Models.AIProviderConfiguration>("POST", "/api/v1/ai-provider-configurations/{config_id}/successors", options);
}

export async function suspend_ai_provider_configuration(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AIProviderConfiguration> {
  return client.request<Models.AIProviderConfiguration>("POST", "/api/v1/ai-provider-configurations/{config_id}/suspend", options);
}

export async function test_ai_provider_connection(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderConnectionTestResult> {
  return client.request<Models.ProviderConnectionTestResult>("POST", "/api/v1/ai-provider-configurations/{config_id}/test-connection", options);
}

export async function get_applicable_regime(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/applicable-regimes/{applicable_regime_id}", options);
}

export async function publish_applicable_regime(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/applicable-regimes/{applicable_regime_id}/publish", options);
}

export async function get_approval_package(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/approval-packages/{approval_package_id}", options);
}

export async function list_approval_applicability_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/approval-packages/{approval_package_id}/applicability-events", options);
}

export async function create_approval_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/approval-packages/{approval_package_id}/approval-requests", options);
}

export async function get_approval_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/approval-requests/{approval_request_id}", options);
}

export async function cancel_approval_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/approval-requests/{approval_request_id}/cancel", options);
}

export async function append_approval_decision(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/approval-steps/{approval_step_id}/decisions", options);
}

export async function list_approval_workflow_versions(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/approval-workflow-versions", options);
}

export async function create_approval_workflow_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/approval-workflow-versions", options);
}

export async function get_approval_workflow_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/approval-workflow-versions/{workflow_version_id}", options);
}

export async function update_approval_workflow_version_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/approval-workflow-versions/{workflow_version_id}", options);
}

export async function archive_approval_workflow_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/approval-workflow-versions/{workflow_version_id}/archive", options);
}

export async function publish_approval_workflow_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/approval-workflow-versions/{workflow_version_id}/publish", options);
}

export async function list_audit_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/audit-events", options);
}

export async function create_audit_integrity_check(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/audit-integrity-checks", options);
}

export async function get_audit_integrity_check(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/audit-integrity-checks/{integrity_check_id}", options);
}

export async function list_calibration_artifacts(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CalibrationArtifactListResponse> {
  return client.request<Models.CalibrationArtifactListResponse>("GET", "/api/v1/calibration-artifacts", options);
}

export async function create_calibration_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CalibrationArtifactVersion> {
  return client.request<Models.CalibrationArtifactVersion>("POST", "/api/v1/calibration-artifacts", options);
}

export async function get_calibration_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CalibrationArtifactVersion> {
  return client.request<Models.CalibrationArtifactVersion>("GET", "/api/v1/calibration-artifacts/{calibration_artifact_id}", options);
}

export async function get_candidate_search_space(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CandidateSearchSpace> {
  return client.request<Models.CandidateSearchSpace>("GET", "/api/v1/candidate-search-spaces/{candidate_search_space_id}", options);
}

export async function get_commercial_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/commercial-policies/{commercial_policie_id}", options);
}

export async function publish_commercial_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/commercial-policies/{commercial_policy_id}/publish", options);
}

export async function get_competitor_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorProfile> {
  return client.request<Models.CompetitorProfile>("GET", "/api/v1/competitor-profiles/{competitor_profile_id}", options);
}

export async function publish_competitor_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorProfile> {
  return client.request<Models.CompetitorProfile>("POST", "/api/v1/competitor-profiles/{competitor_profile_id}/publish", options);
}

export async function get_competitor_source(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorSource> {
  return client.request<Models.CompetitorSource>("GET", "/api/v1/competitor-sources/{competitor_source_id}", options);
}

export async function quarantine_competitor_source(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorSource> {
  return client.request<Models.CompetitorSource>("POST", "/api/v1/competitor-sources/{competitor_source_id}/quarantine", options);
}

export async function review_competitor_source(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorSource> {
  return client.request<Models.CompetitorSource>("POST", "/api/v1/competitor-sources/{competitor_source_id}/review", options);
}

export async function list_competitors(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorListResponse> {
  return client.request<Models.CompetitorListResponse>("GET", "/api/v1/competitors", options);
}

export async function create_competitor(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.Competitor> {
  return client.request<Models.Competitor>("POST", "/api/v1/competitors", options);
}

export async function get_competitor(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.Competitor> {
  return client.request<Models.Competitor>("GET", "/api/v1/competitors/{competitor_id}", options);
}

export async function update_competitor_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.Competitor> {
  return client.request<Models.Competitor>("PATCH", "/api/v1/competitors/{competitor_id}", options);
}

export async function archive_competitor(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.Competitor> {
  return client.request<Models.Competitor>("POST", "/api/v1/competitors/{competitor_id}/archive", options);
}

export async function list_competitor_profiles(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorProfileListResponse> {
  return client.request<Models.CompetitorProfileListResponse>("GET", "/api/v1/competitors/{competitor_id}/profiles", options);
}

export async function build_competitor_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorProfile> {
  return client.request<Models.CompetitorProfile>("POST", "/api/v1/competitors/{competitor_id}/profiles/build", options);
}

export async function list_competitor_sources(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorSourceListResponse> {
  return client.request<Models.CompetitorSourceListResponse>("GET", "/api/v1/competitors/{competitor_id}/sources", options);
}

export async function create_competitor_source(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompetitorSource> {
  return client.request<Models.CompetitorSource>("POST", "/api/v1/competitors/{competitor_id}/sources", options);
}

export async function get_compliance_review(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/compliance-reviews/{compliance_review_id}", options);
}

export async function transition_compliance_review(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/compliance-reviews/{compliance_review_id}/transition", options);
}

export async function get_condition(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/conditions/{condition_id}", options);
}

export async function expire_condition(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/conditions/{condition_id}/expire", options);
}

export async function fail_condition(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/conditions/{condition_id}/fail", options);
}

export async function satisfy_condition(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/conditions/{condition_id}/satisfy", options);
}

export async function waive_condition(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/conditions/{condition_id}/waive", options);
}

export async function append_consent_withdrawal(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/consent-withdrawals", options);
}

export async function get_cost_baseline(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/cost-baselines/{cost_baseline_id}", options);
}

export async function approve_cost_baseline(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/cost-baselines/{cost_baseline_id}/approve", options);
}

export async function publish_cost_baseline(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/cost-baselines/{cost_baseline_id}/publish", options);
}

export async function list_cross_border_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/cross-border-assessments", options);
}

export async function create_cross_border_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/cross-border-assessments", options);
}

export async function get_cross_border_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/cross-border-assessments/{cross_border_assessment_id}", options);
}

export async function approve_cross_border_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/cross-border-assessments/{cross_border_assessment_id}/approve", options);
}

export async function expire_cross_border_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/cross-border-assessments/{cross_border_assessment_id}/expire", options);
}

export async function mark_not_required_cross_border_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/cross-border-assessments/{cross_border_assessment_id}/mark-not-required", options);
}

export async function revoke_cross_border_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/cross-border-assessments/{cross_border_assessment_id}/revoke", options);
}

export async function get_cross_lot_constraint(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/cross-lot-constraints/{cross_lot_constraint_id}", options);
}

export async function confirm_cross_lot_constraint(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/cross-lot-constraints/{cross_lot_constraint_id}/confirm", options);
}

export async function list_data_subject_requests(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/data-subject-requests", options);
}

export async function create_data_subject_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/data-subject-requests", options);
}

export async function get_data_subject_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/data-subject-requests/{data_subject_request_id}", options);
}

export async function complete_data_subject_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/data-subject-requests/{data_subject_request_id}/complete", options);
}

export async function transition_data_subject_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/data-subject-requests/{data_subject_request_id}/transition", options);
}

export async function verify_identity_data_subject_request(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/data-subject-requests/{data_subject_request_id}/verify-identity", options);
}

export async function list_datasets(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DatasetListResponse> {
  return client.request<Models.DatasetListResponse>("GET", "/api/v1/datasets", options);
}

export async function create_dataset(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DatasetSnapshotVersion> {
  return client.request<Models.DatasetSnapshotVersion>("POST", "/api/v1/datasets", options);
}

export async function get_dataset(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DatasetSnapshotVersion> {
  return client.request<Models.DatasetSnapshotVersion>("GET", "/api/v1/datasets/{dataset_id}", options);
}

export async function publish_dataset(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DatasetSnapshotVersion> {
  return client.request<Models.DatasetSnapshotVersion>("POST", "/api/v1/datasets/{dataset_id}/publish", options);
}

export async function get_decision_baseline(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DecisionBaseline> {
  return client.request<Models.DecisionBaseline>("GET", "/api/v1/decision-baselines/{decision_baseline_id}", options);
}

export async function get_decision_report(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-reports/{report_id}", options);
}

export async function download_decision_report(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-reports/{report_id}/download", options);
}

export async function get_decision_unit(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}", options);
}

export async function update_decision_unit_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/decision-units/{unit_id}", options);
}

export async function list_applicable_regimes(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/applicable-regimes", options);
}

export async function create_applicable_regime(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/applicable-regimes", options);
}

export async function list_approval_packages(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/approval-packages", options);
}

export async function freeze_approval_package(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/approval-packages/freeze", options);
}

export async function list_candidate_search_spaces(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SearchSpaceListResponse> {
  return client.request<Models.SearchSpaceListResponse>("GET", "/api/v1/decision-units/{unit_id}/candidate-search-spaces", options);
}

export async function create_candidate_search_space(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CandidateSearchSpace> {
  return client.request<Models.CandidateSearchSpace>("POST", "/api/v1/decision-units/{unit_id}/candidate-search-spaces", options);
}

export async function list_commercial_policies(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/commercial-policies", options);
}

export async function create_commercial_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/commercial-policies", options);
}

export async function list_compliance_reviews(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/compliance-reviews", options);
}

export async function create_compliance_review(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/compliance-reviews", options);
}

export async function list_conditions(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/conditions", options);
}

export async function create_condition(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/conditions", options);
}

export async function list_cost_baselines(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/cost-baselines", options);
}

export async function create_cost_baseline(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/cost-baselines", options);
}

export async function list_cross_lot_constraints(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/cross-lot-constraints", options);
}

export async function create_cross_lot_constraint(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/cross-lot-constraints", options);
}

export async function list_decision_baselines(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.BaselineListResponse> {
  return client.request<Models.BaselineListResponse>("GET", "/api/v1/decision-units/{unit_id}/decision-baselines", options);
}

export async function freeze_decision_baseline(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DecisionBaseline> {
  return client.request<Models.DecisionBaseline>("POST", "/api/v1/decision-units/{unit_id}/decision-baselines/freeze", options);
}

export async function list_decision_reports(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/decision-reports", options);
}

export async function create_decision_report(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/decision-reports", options);
}

export async function create_unit_document_upload_session(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UploadSessionResponse> {
  return client.request<Models.UploadSessionResponse>("POST", "/api/v1/decision-units/{unit_id}/document-upload-sessions", options);
}

export async function list_unit_documents(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DocumentListResponse> {
  return client.request<Models.DocumentListResponse>("GET", "/api/v1/decision-units/{unit_id}/documents", options);
}

export async function list_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/evidence", options);
}

export async function create_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/evidence", options);
}

export async function list_evidence_matches(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/evidence-matches", options);
}

export async function create_evidence_matche(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/evidence-matches", options);
}

export async function list_decision_unit_lifecycle_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/lifecycle-events", options);
}

export async function list_market_priors(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketPriorListResponse> {
  return client.request<Models.MarketPriorListResponse>("GET", "/api/v1/decision-units/{unit_id}/market-priors", options);
}

export async function create_market_prior(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketPriorVersion> {
  return client.request<Models.MarketPriorVersion>("POST", "/api/v1/decision-units/{unit_id}/market-priors", options);
}

export async function create_unit_parse_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ParseJobResponse> {
  return client.request<Models.ParseJobResponse>("POST", "/api/v1/decision-units/{unit_id}/parse-jobs", options);
}

export async function list_precheck_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/precheck-assessments", options);
}

export async function create_precheck_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/precheck-assessments", options);
}

export async function list_precheck_reports(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/precheck-reports", options);
}

export async function create_precheck_report(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/precheck-reports", options);
}

export async function list_procurement_outcomes(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/procurement-outcomes", options);
}

export async function create_procurement_outcome(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/procurement-outcomes", options);
}

export async function list_readiness_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/readiness-assessments", options);
}

export async function create_readiness_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/readiness-assessments", options);
}

export async function list_recommendation_eligibilities(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.EligibilityListResponse> {
  return client.request<Models.EligibilityListResponse>("GET", "/api/v1/decision-units/{unit_id}/recommendation-eligibilities", options);
}

export async function create_recommendation_eligibilitie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RecommendationEligibility> {
  return client.request<Models.RecommendationEligibility>("POST", "/api/v1/decision-units/{unit_id}/recommendation-eligibilities", options);
}

export async function list_requirements(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/requirements", options);
}

export async function create_requirement(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/requirements", options);
}

export async function list_response_profiles(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/response-profiles", options);
}

export async function create_response_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/response-profiles", options);
}

export async function list_risk_acceptances(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RiskAcceptanceListResponse> {
  return client.request<Models.RiskAcceptanceListResponse>("GET", "/api/v1/decision-units/{unit_id}/risk-acceptances", options);
}

export async function create_risk_acceptance(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RiskAcceptance> {
  return client.request<Models.RiskAcceptance>("POST", "/api/v1/decision-units/{unit_id}/risk-acceptances", options);
}

export async function list_rule_sets(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/rule-sets", options);
}

export async function create_rule_set(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/rule-sets", options);
}

export async function list_scenario_sets(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ScenarioSetListResponse> {
  return client.request<Models.ScenarioSetListResponse>("GET", "/api/v1/decision-units/{unit_id}/scenario-sets", options);
}

export async function create_scenario_set(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ScenarioSet> {
  return client.request<Models.ScenarioSet>("POST", "/api/v1/decision-units/{unit_id}/scenario-sets", options);
}

export async function list_scope_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/scope-assessments", options);
}

export async function create_scope_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/scope-assessments", options);
}

export async function list_simulation_assessment_snapshots(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SnapshotListResponse> {
  return client.request<Models.SnapshotListResponse>("GET", "/api/v1/decision-units/{unit_id}/simulation-assessment-snapshots", options);
}

export async function create_simulation_assessment_snapshot(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SimulationAssessmentSnapshot> {
  return client.request<Models.SimulationAssessmentSnapshot>("POST", "/api/v1/decision-units/{unit_id}/simulation-assessment-snapshots", options);
}

export async function list_simulation_batches(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.BatchListResponse> {
  return client.request<Models.BatchListResponse>("GET", "/api/v1/decision-units/{unit_id}/simulation-batches", options);
}

export async function create_simulation_batch(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SimulationBatch> {
  return client.request<Models.SimulationBatch>("POST", "/api/v1/decision-units/{unit_id}/simulation-batches", options);
}

export async function create_subject_deduplication_run(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SubjectDeduplicationRun> {
  return client.request<Models.SubjectDeduplicationRun>("POST", "/api/v1/decision-units/{unit_id}/subject-deduplication-runs", options);
}

export async function list_submission_authorizations(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/submission-authorizations", options);
}

export async function create_submission_authorization(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/submission-authorizations", options);
}

export async function list_submission_records(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/decision-units/{unit_id}/submission-records", options);
}

export async function create_submission_record_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/submission-records", options);
}

export async function submit_decision_unit_transition_command(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/decision-units/{unit_id}/transition-commands", options);
}

export async function list_unknown_entrant_profiles(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UnknownEntrantProfileListResponse> {
  return client.request<Models.UnknownEntrantProfileListResponse>("GET", "/api/v1/decision-units/{unit_id}/unknown-entrant-profiles", options);
}

export async function create_unknown_entrant_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UnknownEntrantProfileVersion> {
  return client.request<Models.UnknownEntrantProfileVersion>("POST", "/api/v1/decision-units/{unit_id}/unknown-entrant-profiles", options);
}

export async function list_deletion_jobs(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/deletion-jobs", options);
}

export async function create_deletion_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/deletion-jobs", options);
}

export async function get_deletion_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/deletion-jobs/{deletion_job_id}", options);
}

export async function list_deletion_receipts(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/deletion-jobs/{deletion_job_id}/receipts", options);
}

export async function list_deletion_replica_commands(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/deletion-jobs/{deletion_job_id}/replica-commands", options);
}

export async function retry_deletion_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/deletion-jobs/{deletion_job_id}/retry", options);
}

export async function get_derived_asset(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DerivedAsset> {
  return client.request<Models.DerivedAsset>("GET", "/api/v1/derived-assets/{derived_asset_id}", options);
}

export async function detach_document_link(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DocumentLink> {
  return client.request<Models.DocumentLink>("POST", "/api/v1/document-links/detach", options);
}

export async function inherit_to_unit_document_link(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DocumentLink> {
  return client.request<Models.DocumentLink>("POST", "/api/v1/document-links/inherit-to-unit", options);
}

export async function override_document_link(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DocumentLink> {
  return client.request<Models.DocumentLink>("POST", "/api/v1/document-links/override", options);
}

export async function resolve_conflict_document_link(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DocumentLink> {
  return client.request<Models.DocumentLink>("POST", "/api/v1/document-links/resolve-conflict", options);
}

export async function get_document_upload_session(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UploadSessionResponse> {
  return client.request<Models.UploadSessionResponse>("GET", "/api/v1/document-upload-sessions/{session_id}", options);
}

export async function cancel_document_upload_session(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UploadSessionResponse> {
  return client.request<Models.UploadSessionResponse>("POST", "/api/v1/document-upload-sessions/{session_id}/cancel", options);
}

export async function put_document_upload_chunk(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UploadSessionResponse> {
  return client.request<Models.UploadSessionResponse>("PUT", "/api/v1/document-upload-sessions/{session_id}/chunks/{part_number}", options);
}

export async function complete_document_upload_session(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CompleteUploadResponse> {
  return client.request<Models.CompleteUploadResponse>("POST", "/api/v1/document-upload-sessions/{session_id}/complete", options);
}

export async function get_document(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SourceDocument> {
  return client.request<Models.SourceDocument>("GET", "/api/v1/documents/{document_id}", options);
}

export async function list_document_derived_assets(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DerivedAssetListResponse> {
  return client.request<Models.DerivedAssetListResponse>("GET", "/api/v1/documents/{document_id}/derived-assets", options);
}

export async function download_document(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("GET", "/api/v1/documents/{document_id}/download", options);
}

export async function quarantine_document(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SourceDocument> {
  return client.request<Models.SourceDocument>("POST", "/api/v1/documents/{document_id}/quarantine", options);
}

export async function release_from_quarantine_document(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SourceDocument> {
  return client.request<Models.SourceDocument>("POST", "/api/v1/documents/{document_id}/release-from-quarantine", options);
}

export async function review_document(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SourceDocument> {
  return client.request<Models.SourceDocument>("POST", "/api/v1/documents/{document_id}/review", options);
}

export async function list_dsr_policies(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/dsr-policies", options);
}

export async function create_dsr_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/dsr-policies", options);
}

export async function get_dsr_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/dsr-policies/{dsr_policie_id}", options);
}

export async function archive_dsr_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/dsr-policies/{dsr_policy_id}/archive", options);
}

export async function publish_dsr_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/dsr-policies/{dsr_policy_id}/publish", options);
}

export async function list_evaluation_protocols(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.EvaluationProtocolListResponse> {
  return client.request<Models.EvaluationProtocolListResponse>("GET", "/api/v1/evaluation-protocols", options);
}

export async function create_evaluation_protocol(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.EvaluationProtocolVersion> {
  return client.request<Models.EvaluationProtocolVersion>("POST", "/api/v1/evaluation-protocols", options);
}

export async function get_evaluation_protocol(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.EvaluationProtocolVersion> {
  return client.request<Models.EvaluationProtocolVersion>("GET", "/api/v1/evaluation-protocols/{evaluation_protocol_id}", options);
}

export async function publish_evaluation_protocol(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.EvaluationProtocolVersion> {
  return client.request<Models.EvaluationProtocolVersion>("POST", "/api/v1/evaluation-protocols/{evaluation_protocol_id}/publish", options);
}

export async function review_evidence_match(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/evidence-matches/{evidence_match_id}/review", options);
}

export async function get_evidence_matche(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/evidence-matches/{evidence_matche_id}", options);
}

export async function get_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/evidence/{evidence_id}", options);
}

export async function publish_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/evidence/{evidence_id}/publish", options);
}

export async function review_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/evidence/{evidence_id}/review", options);
}

export async function revoke_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/evidence/{evidence_id}/revoke", options);
}

export async function list_feature_schemas(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.FeatureSchemaListResponse> {
  return client.request<Models.FeatureSchemaListResponse>("GET", "/api/v1/feature-schemas", options);
}

export async function create_feature_schema(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.FeatureSchemaVersion> {
  return client.request<Models.FeatureSchemaVersion>("POST", "/api/v1/feature-schemas", options);
}

export async function get_feature_schema(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.FeatureSchemaVersion> {
  return client.request<Models.FeatureSchemaVersion>("GET", "/api/v1/feature-schemas/{feature_schema_id}", options);
}

export async function publish_feature_schema(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.FeatureSchemaVersion> {
  return client.request<Models.FeatureSchemaVersion>("POST", "/api/v1/feature-schemas/{feature_schema_id}/publish", options);
}

export async function list_incident_policies(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/incident-policies", options);
}

export async function create_incident_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/incident-policies", options);
}

export async function get_incident_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/incident-policies/{incident_policie_id}", options);
}

export async function approve_incident_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/incident-policies/{incident_policy_id}/approve", options);
}

export async function list_incidents(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/incidents", options);
}

export async function create_incident(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/incidents", options);
}

export async function get_incident(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/incidents/{incident_id}", options);
}

export async function close_incident(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/incidents/{incident_id}/close", options);
}

export async function transition_incident(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/incidents/{incident_id}/transition", options);
}

export async function list_invalidation_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/invalidation-events", options);
}

export async function get_invalidation_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/invalidation-events/{invalidation_id}", options);
}

export async function get_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.JobView> {
  return client.request<Models.JobView>("GET", "/api/v1/jobs/{job_id}", options);
}

export async function cancel_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.JobView> {
  return client.request<Models.JobView>("POST", "/api/v1/jobs/{job_id}/cancel", options);
}

export async function stream_job_events(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("GET", "/api/v1/jobs/{job_id}/events", options);
}

export async function retry_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.JobView> {
  return client.request<Models.JobView>("POST", "/api/v1/jobs/{job_id}/retry", options);
}

export async function list_legal_basis_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/legal-basis-evidence", options);
}

export async function create_legal_basis_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/legal-basis-evidence", options);
}

export async function get_legal_basis_evidence(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/legal-basis-evidence/{legal_basis_evidence_id}", options);
}

export async function create_legal_hold_override(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/legal-hold-overrides", options);
}

export async function list_legal_holds(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/legal-holds", options);
}

export async function create_legal_hold(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/legal-holds", options);
}

export async function release_legal_hold(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/legal-holds/{legal_hold_id}/release", options);
}

export async function list_load_profiles(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/load-profiles", options);
}

export async function create_load_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/load-profiles", options);
}

export async function get_load_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/load-profiles/{load_profile_id}", options);
}

export async function freeze_load_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/load-profiles/{load_profile_id}/freeze", options);
}

export async function list_manual_overrides(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("GET", "/api/v1/manual-overrides", options);
}

export async function append_manual_override(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("POST", "/api/v1/manual-overrides", options);
}

export async function revoke_manual_override(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("POST", "/api/v1/manual-overrides/{override_id}/revoke", options);
}

export async function get_market_prior(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketPriorVersion> {
  return client.request<Models.MarketPriorVersion>("GET", "/api/v1/market-priors/{market_prior_id}", options);
}

export async function publish_market_prior(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketPriorVersion> {
  return client.request<Models.MarketPriorVersion>("POST", "/api/v1/market-priors/{market_prior_id}/publish", options);
}

export async function review_market_prior(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketPriorVersion> {
  return client.request<Models.MarketPriorVersion>("POST", "/api/v1/market-priors/{market_prior_id}/review", options);
}

export async function get_current_user(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MeResponse> {
  return client.request<Models.MeResponse>("GET", "/api/v1/me", options);
}

export async function create_model_approval(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelApprovalVersion> {
  return client.request<Models.ModelApprovalVersion>("POST", "/api/v1/model-approvals", options);
}

export async function decide_model_approval(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelApprovalVersion> {
  return client.request<Models.ModelApprovalVersion>("POST", "/api/v1/model-approvals/{model_approval_id}/decide", options);
}

export async function list_model_artifacts(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelArtifactListResponse> {
  return client.request<Models.ModelArtifactListResponse>("GET", "/api/v1/model-artifacts", options);
}

export async function create_model_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelArtifactVersion> {
  return client.request<Models.ModelArtifactVersion>("POST", "/api/v1/model-artifacts", options);
}

export async function get_model_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelArtifactVersion> {
  return client.request<Models.ModelArtifactVersion>("GET", "/api/v1/model-artifacts/{model_artifact_id}", options);
}

export async function publish_model_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelArtifactVersion> {
  return client.request<Models.ModelArtifactVersion>("POST", "/api/v1/model-artifacts/{model_artifact_id}/publish", options);
}

export async function create_model_deployment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelDeploymentVersion> {
  return client.request<Models.ModelDeploymentVersion>("POST", "/api/v1/model-deployments", options);
}

export async function activate_model_deployment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelDeploymentVersion> {
  return client.request<Models.ModelDeploymentVersion>("POST", "/api/v1/model-deployments/{model_deployment_id}/activate", options);
}

export async function rollback_model_deployment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelDeploymentVersion> {
  return client.request<Models.ModelDeploymentVersion>("POST", "/api/v1/model-deployments/{model_deployment_id}/rollback", options);
}

export async function list_model_incidents(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelIncidentListResponse> {
  return client.request<Models.ModelIncidentListResponse>("GET", "/api/v1/model-incidents", options);
}

export async function create_model_incident(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelIncidentEvent> {
  return client.request<Models.ModelIncidentEvent>("POST", "/api/v1/model-incidents", options);
}

export async function get_model_incident(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelIncidentEvent> {
  return client.request<Models.ModelIncidentEvent>("GET", "/api/v1/model-incidents/{model_incident_id}", options);
}

export async function list_monitoring_snapshots(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MonitoringSnapshotListResponse> {
  return client.request<Models.MonitoringSnapshotListResponse>("GET", "/api/v1/monitoring-snapshots", options);
}

export async function create_monitoring_snapshot(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelMonitoringSnapshot> {
  return client.request<Models.ModelMonitoringSnapshot>("POST", "/api/v1/monitoring-snapshots", options);
}

export async function get_monitoring_snapshot(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ModelMonitoringSnapshot> {
  return client.request<Models.ModelMonitoringSnapshot>("GET", "/api/v1/monitoring-snapshots/{monitoring_snapshot_id}", options);
}

export async function list_notice_consent_records(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/notice-consent-records", options);
}

export async function create_notice_consent_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/notice-consent-records", options);
}

export async function get_notice_consent_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/notice-consent-records/{notice_consent_record_id}", options);
}

export async function get_object_input_manifest(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/objects/{object_type}/{object_id}/input-manifest", options);
}

export async function get_object_lineage(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/objects/{object_type}/{object_id}/lineage", options);
}

export async function get_optimization_run(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.OptimizationRun> {
  return client.request<Models.OptimizationRun>("GET", "/api/v1/optimization-runs/{run_id}", options);
}

export async function finalize_optimization_run(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.OptimizationRun> {
  return client.request<Models.OptimizationRun>("POST", "/api/v1/optimization-runs/{run_id}/finalize", options);
}

export async function invalidate_optimization_run(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.OptimizationRun> {
  return client.request<Models.OptimizationRun>("POST", "/api/v1/optimization-runs/{run_id}/invalidate", options);
}

export async function list_optimization_merge_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MergeAssessmentListResponse> {
  return client.request<Models.MergeAssessmentListResponse>("GET", "/api/v1/optimization-runs/{run_id}/merge-assessments", options);
}

export async function list_optimization_strategy_plans(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.StrategyPlanListResponse> {
  return client.request<Models.StrategyPlanListResponse>("GET", "/api/v1/optimization-runs/{run_id}/strategy-plans", options);
}

export async function list_optimization_stress_test_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.StressAssessmentListResponse> {
  return client.request<Models.StressAssessmentListResponse>("GET", "/api/v1/optimization-runs/{run_id}/stress-test-assessments", options);
}

export async function get_procurement_outcome(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/outcomes/{outcome_id}", options);
}

export async function list_outcome_conflict_resolution_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/outcomes/{outcome_id}/conflict-resolution-events", options);
}

export async function append_outcome_conflict_resolution_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/outcomes/{outcome_id}/conflict-resolution-events", options);
}

export async function mark_conflicting_procurement_outcome(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/outcomes/{outcome_id}/mark-conflicting", options);
}

export async function verify_procurement_outcome(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/outcomes/{outcome_id}/verify", options);
}

export async function get_parse_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ParseJobResponse> {
  return client.request<Models.ParseJobResponse>("GET", "/api/v1/parse-jobs/{parse_job_id}", options);
}

export async function cancel_parse_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ParseJobResponse> {
  return client.request<Models.ParseJobResponse>("POST", "/api/v1/parse-jobs/{parse_job_id}/cancel", options);
}

export async function retry_parse_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ParseJobResponse> {
  return client.request<Models.ParseJobResponse>("POST", "/api/v1/parse-jobs/{parse_job_id}/retry", options);
}

export async function list_pia_records(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/pia-records", options);
}

export async function create_pia_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/pia-records", options);
}

export async function get_pia_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/pia-records/{pia_record_id}", options);
}

export async function approve_pia_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/pia-records/{pia_record_id}/approve", options);
}

export async function revoke_pia_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/pia-records/{pia_record_id}/revoke", options);
}

export async function create_ai_provider_catalog_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderCatalogVersion> {
  return client.request<Models.ProviderCatalogVersion>("POST", "/api/v1/platform/ai-provider-catalog-versions", options);
}

export async function get_ai_provider_catalog_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderCatalogVersion> {
  return client.request<Models.ProviderCatalogVersion>("GET", "/api/v1/platform/ai-provider-catalog-versions/{catalog_id}", options);
}

export async function publish_ai_provider_catalog_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderCatalogVersion> {
  return client.request<Models.ProviderCatalogVersion>("POST", "/api/v1/platform/ai-provider-catalog-versions/{catalog_id}/publish", options);
}

export async function revoke_ai_provider_catalog_version(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderCatalogVersion> {
  return client.request<Models.ProviderCatalogVersion>("POST", "/api/v1/platform/ai-provider-catalog-versions/{catalog_id}/revoke", options);
}

export async function get_precheck_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/precheck-assessments/{precheck_assessment_id}", options);
}

export async function get_precheck_report(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/precheck-reports/{report_id}", options);
}

export async function download_precheck_report(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/precheck-reports/{report_id}/download", options);
}

export async function list_processing_records(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/processing-records", options);
}

export async function create_processing_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/processing-records", options);
}

export async function get_processing_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/processing-records/{processing_record_id}", options);
}

export async function list_projects(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/projects", options);
}

export async function create_project(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/projects", options);
}

export async function get_project(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/projects/{project_id}", options);
}

export async function update_project_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/projects/{project_id}", options);
}

export async function archive_project(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/projects/{project_id}/archive", options);
}

export async function list_decision_units(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/projects/{project_id}/decision-units", options);
}

export async function create_decision_unit(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/projects/{project_id}/decision-units", options);
}

export async function create_project_document_upload_session(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UploadSessionResponse> {
  return client.request<Models.UploadSessionResponse>("POST", "/api/v1/projects/{project_id}/document-upload-sessions", options);
}

export async function list_project_documents(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.DocumentListResponse> {
  return client.request<Models.DocumentListResponse>("GET", "/api/v1/projects/{project_id}/documents", options);
}

export async function create_project_parse_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ParseJobResponse> {
  return client.request<Models.ParseJobResponse>("POST", "/api/v1/projects/{project_id}/parse-jobs", options);
}

export async function list_provider_invocations(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderInvocationPage> {
  return client.request<Models.ProviderInvocationPage>("GET", "/api/v1/provider-invocations", options);
}

export async function get_provider_invocation(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ProviderInvocationRecord> {
  return client.request<Models.ProviderInvocationRecord>("GET", "/api/v1/provider-invocations/{invocation_id}", options);
}

export async function list_provider_policies(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourcePage> {
  return client.request<Models.MarketResourcePage>("GET", "/api/v1/provider-policies", options);
}

export async function create_provider_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/provider-policies", options);
}

export async function get_provider_policie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("GET", "/api/v1/provider-policies/{provider_policie_id}", options);
}

export async function approve_provider_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/provider-policies/{provider_policy_id}/approve", options);
}

export async function expire_provider_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/provider-policies/{provider_policy_id}/expire", options);
}

export async function mark_not_required_provider_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/provider-policies/{provider_policy_id}/mark-not-required", options);
}

export async function revoke_provider_policy(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.MarketResourceRecord> {
  return client.request<Models.MarketResourceRecord>("POST", "/api/v1/provider-policies/{provider_policy_id}/revoke", options);
}

export async function get_readiness_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/readiness-assessments/{readiness_assessment_id}", options);
}

export async function get_recommendation_eligibilitie(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RecommendationEligibility> {
  return client.request<Models.RecommendationEligibility>("GET", "/api/v1/recommendation-eligibilities/{recommendation_eligibilitie_id}", options);
}

export async function list_replicas(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ReplicaListResponse> {
  return client.request<Models.ReplicaListResponse>("GET", "/api/v1/replicas", options);
}

export async function list_report_lifecycle_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/reports/{report_id}/lifecycle-events", options);
}

export async function append_report_lifecycle_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/reports/{report_id}/lifecycle-events", options);
}

export async function list_report_revocation_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/reports/{report_id}/revocation-events", options);
}

export async function append_report_revocation_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/reports/{report_id}/revocation-events", options);
}

export async function get_requirement(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/requirements/{requirement_id}", options);
}

export async function update_requirement_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/requirements/{requirement_id}", options);
}

export async function publish_requirement(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/requirements/{requirement_id}/publish", options);
}

export async function supersede_requirement(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/requirements/{requirement_id}/supersede", options);
}

export async function get_response_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/response-profiles/{response_profile_id}", options);
}

export async function publish_response_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/response-profiles/{response_profile_id}/publish", options);
}

export async function list_retention_jobs(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/retention-jobs", options);
}

export async function create_retention_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/retention-jobs", options);
}

export async function get_retention_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/retention-jobs/{retention_job_id}", options);
}

export async function retry_retention_job(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/retention-jobs/{retention_job_id}/retry", options);
}

export async function get_risk_acceptance(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RiskAcceptance> {
  return client.request<Models.RiskAcceptance>("GET", "/api/v1/risk-acceptances/{risk_acceptance_id}", options);
}

export async function revoke_risk_acceptance(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RiskAcceptance> {
  return client.request<Models.RiskAcceptance>("POST", "/api/v1/risk-acceptances/{risk_acceptance_id}/revoke", options);
}

export async function list_rollback_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RollbackEventListResponse> {
  return client.request<Models.RollbackEventListResponse>("GET", "/api/v1/rollback-events", options);
}

export async function create_rollback_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RollbackEvent> {
  return client.request<Models.RollbackEvent>("POST", "/api/v1/rollback-events", options);
}

export async function get_rollback_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.RollbackEvent> {
  return client.request<Models.RollbackEvent>("GET", "/api/v1/rollback-events/{rollback_event_id}", options);
}

export async function get_rule_clause(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/rule-clauses/{rule_clause_id}", options);
}

export async function update_rule_clause_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/rule-clauses/{rule_clause_id}", options);
}

export async function supersede_rule_clause(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/rule-clauses/{rule_clause_id}/supersede", options);
}

export async function get_rule_set(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/rule-sets/{rule_set_id}", options);
}

export async function list_rule_clauses(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/rule-sets/{rule_set_id}/clauses", options);
}

export async function create_rule_clause(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/rule-sets/{rule_set_id}/clauses", options);
}

export async function publish_rule_set(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/rule-sets/{rule_set_id}/publish", options);
}

export async function get_scenario_set(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ScenarioSet> {
  return client.request<Models.ScenarioSet>("GET", "/api/v1/scenario-sets/{scenario_set_id}", options);
}

export async function freeze_scenario_set(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ScenarioSet> {
  return client.request<Models.ScenarioSet>("POST", "/api/v1/scenario-sets/{scenario_set_id}/freeze", options);
}

export async function get_scope_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/scope-assessments/{scope_assessment_id}", options);
}

export async function update_scope_assessment_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/scope-assessments/{scope_assessment_id}", options);
}

export async function publish_scope_assessment(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/scope-assessments/{scope_assessment_id}/publish", options);
}

export async function get_simulation_assessment_snapshot(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SimulationAssessmentSnapshot> {
  return client.request<Models.SimulationAssessmentSnapshot>("GET", "/api/v1/simulation-assessment-snapshots/{simulation_assessment_snapshot_id}", options);
}

export async function download_simulation_assessment_snapshot(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SnapshotDownloadResponse> {
  return client.request<Models.SnapshotDownloadResponse>("GET", "/api/v1/simulation-assessment-snapshots/{simulation_assessment_snapshot_id}/download", options);
}

export async function get_simulation_batch(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SimulationBatch> {
  return client.request<Models.SimulationBatch>("GET", "/api/v1/simulation-batches/{batch_id}", options);
}

export async function cancel_simulation_batch(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SimulationBatch> {
  return client.request<Models.SimulationBatch>("POST", "/api/v1/simulation-batches/{batch_id}/cancel", options);
}

export async function list_simulation_batch_candidates(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.CandidateListResponse> {
  return client.request<Models.CandidateListResponse>("GET", "/api/v1/simulation-batches/{batch_id}/candidates", options);
}

export async function list_optimization_runs(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.OptimizationRunListResponse> {
  return client.request<Models.OptimizationRunListResponse>("GET", "/api/v1/simulation-batches/{batch_id}/optimization-runs", options);
}

export async function create_optimization_run(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.OptimizationRun> {
  return client.request<Models.OptimizationRun>("POST", "/api/v1/simulation-batches/{batch_id}/optimization-runs", options);
}

export async function retry_simulation_batch(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SimulationBatch> {
  return client.request<Models.SimulationBatch>("POST", "/api/v1/simulation-batches/{batch_id}/retry", options);
}

export async function list_simulation_batch_scenario_assessments(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.AssessmentListResponse> {
  return client.request<Models.AssessmentListResponse>("GET", "/api/v1/simulation-batches/{batch_id}/scenario-assessments", options);
}

export async function list_simulation_batch_scenario_outcomes(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.OutcomeListResponse> {
  return client.request<Models.OutcomeListResponse>("GET", "/api/v1/simulation-batches/{batch_id}/scenario-outcomes", options);
}

export async function list_simulation_batch_static_validations(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.StaticValidationListResponse> {
  return client.request<Models.StaticValidationListResponse>("GET", "/api/v1/simulation-batches/{batch_id}/static-validations", options);
}

export async function list_stage_gates(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.GateListResponse> {
  return client.request<Models.GateListResponse>("GET", "/api/v1/stage-gates", options);
}

export async function get_stage_gate(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.GateAssessment> {
  return client.request<Models.GateAssessment>("GET", "/api/v1/stage-gates/{gate_name}", options);
}

export async function assess_stage_gate(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.GateAssessment> {
  return client.request<Models.GateAssessment>("POST", "/api/v1/stage-gates/{gate_name}/assess", options);
}

export async function decide_stage_gate_waiver(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("POST", "/api/v1/stage-gates/{gate_name}/waivers/decide", options);
}

export async function expire_stage_gate_waiver(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("POST", "/api/v1/stage-gates/{gate_name}/waivers/expire", options);
}

export async function request_stage_gate_waiver(client: BiaiceClient, options: RequestOptions = {}): Promise<void> {
  return client.request<void>("POST", "/api/v1/stage-gates/{gate_name}/waivers/request", options);
}

export async function invalidate_strategy_plan(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.StrategyPlan> {
  return client.request<Models.StrategyPlan>("POST", "/api/v1/strategy-plans/{strategy_plan_id}/invalidate", options);
}

export async function publish_strategy_plan(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.StrategyPlan> {
  return client.request<Models.StrategyPlan>("POST", "/api/v1/strategy-plans/{strategy_plan_id}/publish", options);
}

export async function get_subject_deduplication_run(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.SubjectDeduplicationRun> {
  return client.request<Models.SubjectDeduplicationRun>("GET", "/api/v1/subject-deduplication-runs/{run_id}", options);
}

export async function compare_to_approval_package_submission_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-artifacts/{submission_artifact_id}/compare-to-approval-package", options);
}

export async function freeze_submission_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-artifacts/{submission_artifact_id}/freeze", options);
}

export async function get_submission_authorization(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/submission-authorizations/{submission_authorization_id}", options);
}

export async function block_submission_authorization(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-authorizations/{submission_authorization_id}/block", options);
}

export async function expire_submission_authorization(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-authorizations/{submission_authorization_id}/expire", options);
}

export async function get_submission_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/submission-records/{submission_record_id}", options);
}

export async function update_submission_record_draft(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("PATCH", "/api/v1/submission-records/{submission_record_id}", options);
}

export async function list_submission_artifacts(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/submission-records/{submission_record_id}/artifacts", options);
}

export async function append_submission_artifact(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/artifacts", options);
}

export async function list_submission_attempts(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/submission-records/{submission_record_id}/attempts", options);
}

export async function append_submission_attempt(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/attempts", options);
}

export async function declare_submission_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/declare", options);
}

export async function mark_failed_submission_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/mark-failed", options);
}

export async function mark_mismatch_submission_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/mark-mismatch", options);
}

export async function verify_submission_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/verify", options);
}

export async function withdraw_submission_record(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/submission-records/{submission_record_id}/withdraw", options);
}

export async function list_supersession_events(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/supersession-events", options);
}

export async function append_supersession_event(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("POST", "/api/v1/supersession-events", options);
}

export async function list_tombstones(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/tombstones", options);
}

export async function get_tombstone(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/tombstones/{tombstone_id}", options);
}

export async function get_unknown_entrant_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UnknownEntrantProfileVersion> {
  return client.request<Models.UnknownEntrantProfileVersion>("GET", "/api/v1/unknown-entrant-profiles/{unknown_entrant_profile_id}", options);
}

export async function publish_unknown_entrant_profile(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.UnknownEntrantProfileVersion> {
  return client.request<Models.UnknownEntrantProfileVersion>("POST", "/api/v1/unknown-entrant-profiles/{unknown_entrant_profile_id}/publish", options);
}

export async function get_workflow_instance(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/workflow-instances/{workflow_instance_id}", options);
}

export async function list_approval_steps(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.ContractOnlyResource> {
  return client.request<Models.ContractOnlyResource>("GET", "/api/v1/workflow-instances/{workflow_instance_id}/steps", options);
}

export async function get_liveness(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.HealthResponse> {
  return client.request<Models.HealthResponse>("GET", "/health/live", options);
}

export async function get_readiness(client: BiaiceClient, options: RequestOptions = {}): Promise<Models.HealthResponse> {
  return client.request<Models.HealthResponse>("GET", "/health/ready", options);
}
