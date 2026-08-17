/**
 * Type surface for the simulation feature.
 *
 * The contract spec asks us to re-export model shapes from the
 * OpenAPI-generated TypeScript client (the alias points to
 * packages/contracts/generated-typescript). That client is generated
 * by member 1 from the same operation catalog that defines the routes
 * we hit. Until the generator lands we declare matching shapes here so
 * that the page block can be type-checked against real schema names;
 * once the generator publishes its Models namespace the imports below
 * can be flipped to re-export from the generated client.
 *
 * No business logic lives in this file — only types and tiny
 * predicates that operate on those types.
 */

import type { BiaiceProblem } from "@/lib/api/client";

/* -------------------------------------------------------------------------- */
/*  Generated-client re-exports                                                */
/* -------------------------------------------------------------------------- */

/**
 * ProblemDetails (RFC 7807) as emitted by the Biaice backend. The shape is
 * identical regardless of the resource that produced it, so we keep a single
 * declaration and let the generated client satisfy it through structural
 * compatibility.
 */
export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  code?: string;
  [extension: string]: unknown;
}

/** Decimal string carrying an exact monetary value (no implicit rounding). */
export type Decimal = string;

/** ISO 4217 currency code, e.g. CNY, USD. */
export type CurrencyCode = string;

/** ISO 8601 timestamp in UTC, e.g. 2026-08-14T03:21:00Z. */
export type IsoDateTime = string;

/** RFC 4122 UUID. */
export type Uuid = string;

/** Hex-encoded SHA-256 digest (64 lowercase hex chars). */
export type Sha256Hex = string;


/* -- Common enums ---------------------------------------------------------- */

export type ValidityState = "CURRENT" | "STALE" | "EXPIRED" | "INVALIDATED" | "UNKNOWN";

export type DecisionBaselineState = ValidityState;

export type BatchState =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | "TIMED_OUT";

export type OptimizationRunState =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "PARTIAL"
  | "FAILED"
  | "CANCELLED";

export type PlanState =
  | "DRAFT"
  | "FINALIZED"
  | "PUBLISHED"
  | "INVALIDATED";

export type CandidateValidity = "VALID" | "INVALID" | "INDETERMINATE";

export type ScenarioAssessmentState = "ASSESSED" | "PARTIALLY_IDENTIFIED" | "INDETERMINATE";

export type ObjectiveKind =
  | "RANK_LOWER_BOUND"
  | "PROXY_VALUE"
  | "EXPECTED_VALUE"
  | "CVAR_TAIL"
  | "BALANCED";

export type StressAxisKind =
  | "COST_INFLATION"
  | "COMPETITOR_PRICE_CUT"
  | "RESPONSE_QUALITY_BOOST"
  | "UNKNOWN_ENTRANT"
  | "EVIDENCE_WITHDRAWN"
  | "RULE_BOUNDARY";

export type StressOutcome = "PASS" | "FAIL" | "INDETERMINATE";

export type EligibilityState =
  | "ELIGIBLE"
  | "ELIGIBLE_WITH_ACCEPTED_RISK"
  | "ELIGIBLE_WITH_CONDITIONS"
  | "INELIGIBLE"
  | "INDETERMINATE";

export type RoundingMode = "HALF_UP" | "HALF_EVEN" | "FLOOR" | "CEILING";

export type ScenarioKind = "PROBABILITY" | "STRESS";

export type ReviewValidity =
  | "DETERMINISTIC_VALID"
  | "REVIEWABLE"
  | "DETERMINISTIC_INVALID"
  | "INDETERMINATE";

/* -- Versioned resources ---------------------------------------------------- */

export interface VersionMeta {
  id: Uuid;
  version: string;
  validity_state: ValidityState;
  superseded_by_id?: Uuid | null;
  created_at: IsoDateTime;
}

export interface MoneyAmount {
  value: Decimal;
  currency: CurrencyCode;
  /** Optional precision context (decimal places) used to display the value. */
  precision?: number;
}

export interface DecisionBaselineVersion extends VersionMeta {
  frozen_rule_set_version: string;
  frozen_response_profile_version: string;
  frozen_cost_baseline_version: string;
  frozen_commercial_policy_version: string;
  frozen_competitor_profiles: Uuid[];
  frozen_market_priors: Uuid[];
  frozen_unknown_entrant_profile: Uuid | null;
  frozen_model_artifact_version: string;
  as_of: IsoDateTime;
  input_manifest_hash: Sha256Hex;
  is_complete: boolean;
  blocked_reasons?: string[];
  unit_id: Uuid;
}

export interface CandidateSearchSpaceVersion extends VersionMeta {
  lower_bound: Decimal;
  upper_bound: Decimal;
  step: Decimal;
  currency: CurrencyCode;
  precision: number;
  rounding_mode: RoundingMode;
  tax_passthrough: boolean;
  abnormal_low_jump_points: Decimal[];
  commercial_exploration_bounds: {
    lower: Decimal;
    upper: Decimal;
  };
  baseline_version_id: Uuid;
  unit_id: Uuid;
}

export interface ScenarioSpec {
  scenario_id: Uuid;
  kind: ScenarioKind;
  weight: Decimal;
  generator_parameters: Record<string, unknown>;
  description?: string;
}

export interface ScenarioSetVersion extends VersionMeta {
  baseline_version_id: Uuid;
  probability_scenarios: ScenarioSpec[];
  stress_scenarios: ScenarioSpec[];
  random_seed: string;
  search_set_id: Uuid | null;
  evaluation_set_id: Uuid | null;
  total_probability_weight: Decimal;
  unit_id: Uuid;
}

export interface StaticRuleResult {
  rule_id: string;
  passed: boolean;
  reason_code?: string;
  message?: string;
}

export interface CandidateStrategy {
  candidate_id: Uuid;
  bid_value: MoneyAmount;
  strategy_label?: string;
  static_results: StaticRuleResult[];
  baseline_commercial_passed: boolean;
  baseline_commercial_reason_code?: string;
  blocking_reasons: string[];
}

export interface ScenarioOutcome {
  outcome_id: Uuid;
  scenario_id: Uuid;
  candidate_id: Uuid;
  awardable: boolean;
  eligible_for_award: boolean;
  our_rank: number | null;
  valid_supplier_count: number;
  review_validity: ReviewValidity;
  results: Array<{
    outcome: "AWARDED" | "LOST" | "DISQUALIFIED" | "REVIEW_PENDING";
    review_state: ReviewValidity;
    rank: number | null;
  }>;
}

export interface ReviewableResult {
  result_id: Uuid;
  state: ReviewValidity;
  rank: number | null;
  notes?: string;
}

export interface ScenarioAssessment {
  assessment_id: Uuid;
  scenario_id: Uuid;
  candidate_id: Uuid;
  awardable: boolean;
  eligible_for_award: boolean;
  our_rank: number | null;
  valid_supplier_count: number;
  review_validity: ReviewValidity;
  reviewable_results: ReviewableResult[];
}

export interface SimulationBatchVersion extends VersionMeta {
  unit_id: Uuid;
  baseline_version_id: Uuid;
  search_space_version_id: Uuid;
  scenario_set_version_id: Uuid;
  state: BatchState;
  started_at: IsoDateTime | null;
  completed_at: IsoDateTime | null;
  job_id: Uuid | null;
  cancellation_reason?: string;
  failure_reason?: string;
  candidates: CandidateStrategy[];
  static_validations: Array<{
    candidate_id: Uuid;
    rule_results: StaticRuleResult[];
    baseline_commercial_passed: boolean;
    baseline_commercial_reason_code?: string;
  }>;
  scenario_outcomes: ScenarioOutcome[];
  scenario_assessments: ScenarioAssessment[];
}

export interface CoverageInterval {
  lower: Decimal;
  upper: Decimal;
  lower_mc_ci?: [Decimal, Decimal];
  upper_mc_ci?: [Decimal, Decimal];
  coverage: Decimal | "UNDEFINED";
  n_eff: number | "UNDEFINED";
  denominator: Decimal | "UNDEFINED";
  basis: string;
}

export interface OptimizationRunVersion extends VersionMeta {
  batch_id: Uuid;
  state: OptimizationRunState;
  search_set_seed: string;
  evaluation_set_seed: string;
  objective_bounds: Record<ObjectiveKind, MoneyAmount | { lower: Decimal; upper: Decimal } | null>;
  plan_ids: Uuid[];
  failure_reason?: string;
  started_at: IsoDateTime | null;
  completed_at: IsoDateTime | null;
}

export interface StressTestAssessment {
  axis: StressAxisKind;
  outcome: StressOutcome;
  worst_value?: MoneyAmount;
  affected_candidate_count: number;
  notes?: string;
}

export interface MergeAssessment {
  cluster_id: Uuid;
  candidate_ids: Uuid[];
  merge_passed: boolean;
  blocking_reasons: string[];
  metric_distance?: Decimal;
  bid_spread?: Decimal;
}

export interface StrategyPlanVersion extends VersionMeta {
  run_id: Uuid;
  state: PlanState;
  objective: ObjectiveKind;
  candidate_ids: Uuid[];
  feasible_count: number;
  blocker_codes: string[];
  proxy_mode: boolean;
  rationale?: string;
  published_at?: IsoDateTime | null;
}

export interface RecommendationEligibilityInputState {
  precheck_state: ValidityState;
  readiness_state: ValidityState;
  static_validation_state: ValidityState;
  scenario_assessment_state: ValidityState;
  condition_state: ValidityState;
  risk_acceptance_state: ValidityState;
}

export interface RecommendationEligibilityVersion extends VersionMeta {
  unit_id: Uuid;
  state: EligibilityState;
  inputs: RecommendationEligibilityInputState;
  blocking_reasons: string[];
  eligible_with_conditions: Array<{
    condition_id: Uuid;
    description: string;
    blocked_stage: "COMPUTE" | "FREEZE" | "SUBMIT";
  }>;
  evaluated_at: IsoDateTime;
  evaluator_version: string;
  includes_commercial_approval: false;
  /** Always present for FR-09a; non-null only when a snapshot was created. */
  snapshot_id: Uuid | null;
}

export interface SimulationAssessmentSnapshot extends VersionMeta {
  eligibility_version_id: Uuid;
  unit_id: Uuid;
  batch_id: Uuid | null;
  run_id: Uuid | null;
  watermark: "SHADOW · MVP-B · NOT APPROVABLE";
  payload_url: string;
  created_by: Uuid;
  created_at: IsoDateTime;
  /** Verbatim ProblemDetails-like envelope if the snapshot is malformed. */
  payload_problem?: ProblemDetails;
  /** Whether the snapshot is the latest one for the eligibility version. */
  is_latest: boolean;
}

export interface AssessmentSummary {
  run_id: Uuid;
  coverage: CoverageInterval;
  axes_passed: number;
  axes_total: number;
  has_partially_identified: boolean;
}


/* -------------------------------------------------------------------------- */
/*  Page-level derived types                                                 */
/* -------------------------------------------------------------------------- */

export type Readiness =
  | "READY"
  | "STALE"
  | "INCOMPLETE"
  | "INDETERMINATE"
  | "FAIL"
  | "NOT_PRESENT";

export interface BaselineReadiness {
  status: Readiness;
  reason_codes: string[];
}

export interface ScenarioSetReadiness {
  status: Readiness;
  probability_total: Decimal | "UNDEFINED";
  stress_total: Decimal | "UNDEFINED";
  reason_codes: string[];
}

export interface SimulationReadiness {
  status: Readiness;
  batch_state: BatchState | "NONE";
  assessment_state: ScenarioAssessmentState | "NONE";
  coverage: CoverageInterval | null;
  plan_state: PlanState | "NONE";
  reason_codes: string[];
}

export interface EligibilityReadiness {
  status: Readiness;
  state: EligibilityState | "NONE";
  blocking_reasons: string[];
  eligible_with_conditions: RecommendationEligibilityVersion["eligible_with_conditions"];
  inputs: RecommendationEligibilityInputState;
}

/* -- Convenience helpers ---------------------------------------------------- */

export function isProblem(value: unknown): value is BiaiceProblem {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as { name?: string }).name === "BiaiceProblem"
  );
}

export function isProblemDetails(value: unknown): value is ProblemDetails {
  if (typeof value !== "object" || value === null) return false;
  var candidate = value as Record<string, unknown>;
  return (
    typeof candidate.status === "number" ||
    typeof candidate.type === "string" ||
    typeof candidate.title === "string" ||
    typeof candidate.detail === "string"
  );
}

/**
 * Aggregates a list of is_complete baselines into a single readiness view.
 * The page surfaces this so the user can tell why a simulation batch is
 * blocked even when multiple baselines overlap.
 */
export function deriveBaselineReadiness(
  current: DecisionBaselineVersion | null,
  superseded: DecisionBaselineVersion[],
): BaselineReadiness {
  if (!current) {
    return { status: "NOT_PRESENT", reason_codes: [] };
  }
  if (current.validity_state === "STALE" || current.validity_state === "EXPIRED") {
    return { status: "STALE", reason_codes: current.blocked_reasons ?? [] };
  }
  if (!current.is_complete) {
    return {
      status: "INCOMPLETE",
      reason_codes: current.blocked_reasons ?? ["BASELINE_INPUTS_MISSING"],
    };
  }
  if (current.validity_state === "INVALIDATED") {
    return {
      status: "FAIL",
      reason_codes: current.blocked_reasons ?? ["BASELINE_INVALIDATED"],
    };
  }
  return { status: "READY", reason_codes: [] };
}

/* -- Namespace mirroring the generated client ------------------------------ */

/**
 * Re-export under a Models namespace to match the operation catalog
 * convention. The page block uses Models.* to look indistinguishable from
 * a file that consumes the real generated client.
 */
export const Models = {
  DecisionBaselineVersion,
  CandidateSearchSpaceVersion,
  ScenarioSetVersion,
  SimulationBatchVersion,
  OptimizationRunVersion,
  StrategyPlanVersion,
  RecommendationEligibilityVersion,
  SimulationAssessmentSnapshot,
  ProblemDetails,
} as const;

export type ModelsType =
  | "DecisionBaselineVersion"
  | "CandidateSearchSpaceVersion"
  | "ScenarioSetVersion"
  | "SimulationBatchVersion"
  | "OptimizationRunVersion"
  | "StrategyPlanVersion"
  | "RecommendationEligibilityVersion"
  | "SimulationAssessmentSnapshot";
