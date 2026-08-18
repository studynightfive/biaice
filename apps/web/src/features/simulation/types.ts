/** Shared simulation types derived from the generated OpenAPI contract. */

import type { BiaiceProblem } from "@/lib/api/client";
import type {
  BaselineState,
  DecisionBaseline,
  ProblemDetails,
} from "@biaice/contracts";

export type {
  AssessmentListResponse,
  AwardMode,
  BaselineListResponse,
  BaselineState,
  BatchListResponse,
  BatchState,
  CandidateListResponse,
  CandidateSearchSpace,
  CreateBatchRequest,
  CreateOptimizationRunRequest,
  CreateScenarioSetRequest,
  CreateSearchSpaceRequest,
  DecisionBaseline,
  EligibilityListResponse,
  EligibilityState,
  FreezeBaselineRequest,
  MergeAssessment,
  MergeAssessmentListResponse,
  ObjectiveKind,
  OptimizationRun,
  OptimizationRunListResponse,
  OptimizationState,
  OutcomeListResponse,
  PlanState,
  ProblemDetails,
  RecommendationEligibility,
  RecommendationEligibilityRequest,
  ReviewValidity,
  ScenarioOutcome,
  ScenarioSet,
  ScenarioSetListResponse,
  ScenarioStrategyAssessment,
  SearchSpaceListResponse,
  SimulationAssessmentSnapshot,
  SimulationBatch,
  SimulationCandidate,
  SnapshotDownloadResponse,
  SnapshotListResponse,
  SnapshotRequest,
  StaticCandidateValidation,
  StaticValidationListResponse,
  StrategyPlan,
  StrategyPlanListResponse,
  StressAssessmentListResponse,
  StressAxis,
  StressTestAssessment,
} from "@biaice/contracts";

export type Decimal = string;
export type CurrencyCode = string;
export type Sha256Hex = string;
export type Uuid = string;

export type Readiness =
  | "READY"
  | "STALE"
  | "INCOMPLETE"
  | "FAIL"
  | "NOT_PRESENT";

export interface BaselineReadiness {
  readonly status: Readiness;
  readonly reasonCodes: ReadonlyArray<string>;
}

const BASELINE_READINESS: Record<BaselineState, BaselineReadiness> = {
  DRAFT: { status: "INCOMPLETE", reasonCodes: ["BASELINE_NOT_FROZEN"] },
  FROZEN: { status: "READY", reasonCodes: [] },
  SUPERSEDED: { status: "STALE", reasonCodes: ["BASELINE_SUPERSEDED"] },
  INVALIDATED: { status: "FAIL", reasonCodes: ["BASELINE_INVALIDATED"] },
};

export function deriveBaselineReadiness(
  current: DecisionBaseline | null,
): BaselineReadiness {
  if (!current) return { status: "NOT_PRESENT", reasonCodes: [] };
  return BASELINE_READINESS[current.state];
}

export function isProblem(value: unknown): value is BiaiceProblem {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as { name?: string }).name === "BiaiceProblem"
  );
}

export function isProblemDetails(value: unknown): value is ProblemDetails {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.status === "number" ||
    typeof candidate.type === "string" ||
    typeof candidate.title === "string" ||
    typeof candidate.detail === "string"
  );
}
