/**
 * Server-side data layer for the simulation feature.
 *
 * Every fetch in this file goes through `getBiaiceClient()` so the
 * generated client is the only place that knows about HTTP plumbing.
 * The simulation page block must run on the server (Server Components)
 * so it can call these fetchers directly with the Next.js 16
 * `no-store` cache policy and the most recent backend state.
 *
 * No fake data is permitted: when the backend is unreachable or
 * returns an error, the caller receives the raw `BiaiceProblem` and
 * the React error boundary renders the failure. We never fabricate
 * a successful response.
 */

import "server-only";

import { randomUUID } from "node:crypto";

import { getBiaiceClient, type BiaiceClient } from "@/lib/api/client";
import type {
  CandidateSearchSpaceVersion,
  CoverageInterval,
  Decimal,
  DecisionBaselineVersion,
  MergeAssessment,
  OptimizationRunVersion,
  RecommendationEligibilityVersion,
  ScenarioAssessment,
  ScenarioOutcome,
  ScenarioSetVersion,
  SimulationAssessmentSnapshot,
  SimulationBatchVersion,
  StaticRuleResult,
  StrategyPlanVersion,
  StressTestAssessment,
  Uuid,
} from "./types";

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const NO_STORE: RequestCache = "no-store";
const NEXT_REVALIDATE = { revalidate: 0 } as const;

/** Builds a stable idempotency key from a logical action + caller. */
export function newIdempotencyKey(action: string, hint?: string): string {
  const suffix = hint ? ":" + hint : "";
  return action + ":" + randomUUID() + suffix;
}

function client(): BiaiceClient {
  return getBiaiceClient();
}

function withIdempotency(opts: { idempotencyKey?: string }) {
  return {
    cache: NO_STORE,
    next: NEXT_REVALIDATE,
    idempotencyKey: opts.idempotencyKey,
  };
}

function readOnly() {
  return { cache: NO_STORE, next: NEXT_REVALIDATE };
}

/* -------------------------------------------------------------------------- */
/*  Decision baselines (FR-06)                                                */
/* -------------------------------------------------------------------------- */

export function listDecisionBaselines(unitId: Uuid): Promise<DecisionBaselineVersion[]> {
  return client().request<DecisionBaselineVersion[]>("GET", `/api/v1/decision-units/${unitId}/decision-baselines`, readOnly());
}

export function getDecisionBaseline(baselineId: Uuid): Promise<DecisionBaselineVersion> {
  return client().request<DecisionBaselineVersion>("GET", `/api/v1/decision-baselines/${baselineId}`, readOnly());
}

export function freezeDecisionBaseline(
  unitId: Uuid,
  body: { input_manifest_hash?: string; as_of?: string },
  idempotencyKey?: string,
): Promise<DecisionBaselineVersion> {
  return client().request<DecisionBaselineVersion>("POST", `/api/v1/decision-units/${unitId}/decision-baselines/freeze`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("freeze_decision_baseline", unitId) }),
    body,
  });
}

/* -------------------------------------------------------------------------- */
/*  Candidate search spaces (FR-06)                                           */
/* -------------------------------------------------------------------------- */

export function listSearchSpaces(unitId: Uuid): Promise<CandidateSearchSpaceVersion[]> {
  return client().request<CandidateSearchSpaceVersion[]>("GET", `/api/v1/decision-units/${unitId}/candidate-search-spaces`, readOnly());
}

export function createSearchSpace(
  unitId: Uuid,
  body: {
    baseline_version_id: Uuid;
    lower_bound: Decimal;
    upper_bound: Decimal;
    step: Decimal;
    currency: string;
    precision: number;
    rounding_mode: CandidateSearchSpaceVersion["rounding_mode"];
    tax_passthrough: boolean;
    abnormal_low_jump_points?: Decimal[];
    commercial_exploration_bounds?: { lower: Decimal; upper: Decimal };
  },
  idempotencyKey?: string,
): Promise<CandidateSearchSpaceVersion> {
  return client().request<CandidateSearchSpaceVersion>("POST", `/api/v1/decision-units/${unitId}/candidate-search-spaces`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("create_candidate_search_space", unitId) }),
    body,
  });
}

/* -------------------------------------------------------------------------- */
/*  Scenario sets (FR-06)                                                     */
/* -------------------------------------------------------------------------- */

export function listScenarioSets(unitId: Uuid): Promise<ScenarioSetVersion[]> {
  return client().request<ScenarioSetVersion[]>("GET", `/api/v1/decision-units/${unitId}/scenario-sets`, readOnly());
}

export function getScenarioSet(scenarioSetId: Uuid): Promise<ScenarioSetVersion> {
  return client().request<ScenarioSetVersion>("GET", `/api/v1/scenario-sets/${scenarioSetId}`, readOnly());
}

export function freezeScenarioSet(
  scenarioSetId: Uuid,
  idempotencyKey?: string,
): Promise<ScenarioSetVersion> {
  return client().request<ScenarioSetVersion>("POST", `/api/v1/scenario-sets/${scenarioSetId}/freeze`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("freeze_scenario_set", scenarioSetId) }),
    body: {},
  });
}


/* -------------------------------------------------------------------------- */
/*  Simulation batches (FR-07)                                                */
/* -------------------------------------------------------------------------- */

export function listBatches(unitId: Uuid): Promise<SimulationBatchVersion[]> {
  return client().request<SimulationBatchVersion[]>("GET", `/api/v1/decision-units/${unitId}/simulation-batches`, readOnly());
}

export function getBatch(batchId: Uuid): Promise<SimulationBatchVersion> {
  return client().request<SimulationBatchVersion>("GET", `/api/v1/simulation-batches/${batchId}`, readOnly());
}

export function createBatch(
  unitId: Uuid,
  body: {
    baseline_version_id: Uuid;
    search_space_version_id: Uuid;
    scenario_set_version_id: Uuid;
  },
  idempotencyKey?: string,
): Promise<SimulationBatchVersion> {
  return client().request<SimulationBatchVersion>("POST", `/api/v1/decision-units/${unitId}/simulation-batches`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("create_simulation_batch", unitId) }),
    body,
  });
}

export function cancelBatch(batchId: Uuid, idempotencyKey?: string): Promise<SimulationBatchVersion> {
  return client().request<SimulationBatchVersion>("POST", `/api/v1/simulation-batches/${batchId}/cancel`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("cancel_simulation_batch", batchId) }),
    body: {},
  });
}

export function retryBatch(batchId: Uuid, idempotencyKey?: string): Promise<SimulationBatchVersion> {
  return client().request<SimulationBatchVersion>("POST", `/api/v1/simulation-batches/${batchId}/retry`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("retry_simulation_batch", batchId) }),
    body: {},
  });
}

export interface BatchChildren {
  candidates: unknown[];
  static_validations: Array<{ candidate_id: Uuid; rule_results: StaticRuleResult[]; baseline_commercial_passed: boolean; baseline_commercial_reason_code?: string }>;
  scenario_outcomes: ScenarioOutcome[];
  scenario_assessments: ScenarioAssessment[];
}

export async function listBatchChildren(batchId: Uuid): Promise<BatchChildren> {
  const [candidates, staticValidations, scenarioOutcomes, scenarioAssessments] = await Promise.all([
    client().request<unknown[]>("GET", `/api/v1/simulation-batches/${batchId}/candidates`, readOnly()),
    client().request<BatchChildren["static_validations"]>("GET", `/api/v1/simulation-batches/${batchId}/static-validations`, readOnly()),
    client().request<ScenarioOutcome[]>("GET", `/api/v1/simulation-batches/${batchId}/scenario-outcomes`, readOnly()),
    client().request<ScenarioAssessment[]>("GET", `/api/v1/simulation-batches/${batchId}/scenario-assessments`, readOnly()),
  ]);
  return {
    candidates,
    static_validations: staticValidations,
    scenario_outcomes: scenarioOutcomes,
    scenario_assessments: scenarioAssessments,
  };
}
/* -------------------------------------------------------------------------- */
/*  Optimization runs (FR-08)                                                */
/* -------------------------------------------------------------------------- */

export function listOptimizationRuns(batchId: Uuid): Promise<OptimizationRunVersion[]> {
  return client().request<OptimizationRunVersion[]>("GET", `/api/v1/simulation-batches/${batchId}/optimization-runs`, readOnly());
}

export function getOptimizationRun(runId: Uuid): Promise<OptimizationRunVersion> {
  return client().request<OptimizationRunVersion>("GET", `/api/v1/optimization-runs/${runId}`, readOnly());
}

export function createOptimizationRun(
  batchId: Uuid,
  body: {
    search_set_seed: string;
    evaluation_set_seed: string;
    objectives: ReadonlyArray<"RANK_LOWER_BOUND" | "PROXY_VALUE" | "EXPECTED_VALUE" | "CVAR_TAIL" | "BALANCED">;
  },
  idempotencyKey?: string,
): Promise<OptimizationRunVersion> {
  return client().request<OptimizationRunVersion>("POST", `/api/v1/simulation-batches/${batchId}/optimization-runs`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("create_optimization_run", batchId) }),
    body,
  });
}

export function finalizeOptimizationRun(runId: Uuid, idempotencyKey?: string): Promise<OptimizationRunVersion> {
  return client().request<OptimizationRunVersion>("POST", `/api/v1/optimization-runs/${runId}/finalize`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("finalize_optimization_run", runId) }),
    body: {},
  });
}

export function invalidateOptimizationRun(runId: Uuid, idempotencyKey?: string): Promise<OptimizationRunVersion> {
  return client().request<OptimizationRunVersion>("POST", `/api/v1/optimization-runs/${runId}/invalidate`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("invalidate_optimization_run", runId) }),
    body: {},
  });
}

/* -------------------------------------------------------------------------- */
/*  Strategy plans (FR-08)                                                    */
/* -------------------------------------------------------------------------- */

export function listStrategyPlans(runId: Uuid): Promise<StrategyPlanVersion[]> {
  return client().request<StrategyPlanVersion[]>("GET", `/api/v1/optimization-runs/${runId}/strategy-plans`, readOnly());
}

export function publishStrategyPlan(planId: Uuid, idempotencyKey?: string): Promise<StrategyPlanVersion> {
  return client().request<StrategyPlanVersion>("POST", `/api/v1/strategy-plans/${planId}/publish`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("publish_strategy_plan", planId) }),
    body: {},
  });
}

export function invalidateStrategyPlan(planId: Uuid, idempotencyKey?: string): Promise<StrategyPlanVersion> {
  return client().request<StrategyPlanVersion>("POST", `/api/v1/strategy-plans/${planId}/invalidate`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("invalidate_strategy_plan", planId) }),
    body: {},
  });
}

export function listStressAssessments(runId: Uuid): Promise<StressTestAssessment[]> {
  return client().request<StressTestAssessment[]>("GET", `/api/v1/optimization-runs/${runId}/stress-test-assessments`, readOnly());
}

export function listMergeAssessments(runId: Uuid): Promise<MergeAssessment[]> {
  return client().request<MergeAssessment[]>("GET", `/api/v1/optimization-runs/${runId}/merge-assessments`, readOnly());
}

/* -------------------------------------------------------------------------- */
/*  Recommendation eligibility (FR-09a)                                       */
/* -------------------------------------------------------------------------- */

export function listEligibilities(unitId: Uuid): Promise<RecommendationEligibilityVersion[]> {
  return client().request<RecommendationEligibilityVersion[]>("GET", `/api/v1/decision-units/${unitId}/recommendation-eligibilities`, readOnly());
}

export function getEligibility(eligibilityId: Uuid): Promise<RecommendationEligibilityVersion> {
  return client().request<RecommendationEligibilityVersion>("GET", `/api/v1/recommendation-eligibilities/${eligibilityId}`, readOnly());
}

export function createRecommendationEligibility(
  unitId: Uuid,
  body: { batch_id?: Uuid; run_id?: Uuid; create_snapshot?: boolean },
  idempotencyKey?: string,
): Promise<RecommendationEligibilityVersion> {
  return client().request<RecommendationEligibilityVersion>("POST", `/api/v1/decision-units/${unitId}/recommendation-eligibilities`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("create_recommendation_eligibility", unitId) }),
    body,
  });
}

/* -------------------------------------------------------------------------- */
/*  Simulation assessment snapshots (FR-09a)                                  */
/* -------------------------------------------------------------------------- */

export function listSnapshots(unitId: Uuid): Promise<SimulationAssessmentSnapshot[]> {
  return client().request<SimulationAssessmentSnapshot[]>("GET", `/api/v1/decision-units/${unitId}/simulation-assessment-snapshots`, readOnly());
}

export function getSnapshot(snapshotId: Uuid): Promise<SimulationAssessmentSnapshot> {
  return client().request<SimulationAssessmentSnapshot>("GET", `/api/v1/simulation-assessment-snapshots/${snapshotId}`, readOnly());
}

export function createSnapshot(
  unitId: Uuid,
  body: { eligibility_version_id: Uuid },
  idempotencyKey?: string,
): Promise<SimulationAssessmentSnapshot> {
  return client().request<SimulationAssessmentSnapshot>("POST", `/api/v1/decision-units/${unitId}/simulation-assessment-snapshots`, {
    ...withIdempotency({ idempotencyKey: idempotencyKey ?? newIdempotencyKey("create_simulation_assessment_snapshot", unitId) }),
    body,
  });
}

export function downloadSnapshot(snapshotId: Uuid): Promise<unknown> {
  return client().request<unknown>("GET", `/api/v1/simulation-assessment-snapshots/${snapshotId}/download`, readOnly());
}

/* -------------------------------------------------------------------------- */
/*  Convenience aggregates used by Server Components                          */
/* -------------------------------------------------------------------------- */

export interface BaselineBundle {
  current: DecisionBaselineVersion | null;
  superseded: DecisionBaselineVersion[];
  searchSpaces: CandidateSearchSpaceVersion[];
  scenarioSets: ScenarioSetVersion[];
}

export async function loadBaselineBundle(unitId: Uuid): Promise<BaselineBundle> {
  const [baselines, spaces, sets] = await Promise.all([listDecisionBaselines(unitId), listSearchSpaces(unitId), listScenarioSets(unitId)]);
  const current = baselines.find((b) => b.validity_state === "CURRENT") ?? null;
  const superseded = baselines.filter((b) => b.validity_state !== "CURRENT");
  return { current, superseded, searchSpaces: spaces, scenarioSets: sets };
}

export interface SimulationBundle {
  batches: SimulationBatchVersion[];
  latestBatch: SimulationBatchVersion | null;
  latestBatchChildren: BatchChildren | null;
  latestRun: OptimizationRunVersion | null;
  plans: StrategyPlanVersion[];
  stress: StressTestAssessment[];
  merges: MergeAssessment[];
  coverage: CoverageInterval | null;
}

export async function loadSimulationBundle(
  unitId: Uuid,
  eligibility?: RecommendationEligibilityVersion | null,
): Promise<SimulationBundle> {
  const batches = await listBatches(unitId);
  const latestBatch = batches.find((b) => b.state === "SUCCEEDED") ?? batches[0] ?? null;
  let latestBatchChildren: BatchChildren | null = null;
  let latestRun: OptimizationRunVersion | null = null;
  let plans: StrategyPlanVersion[] = [];
  let stress: StressTestAssessment[] = [];
  let merges: MergeAssessment[] = [];
  if (latestBatch) {
    latestBatchChildren = await listBatchChildren(latestBatch.id);
    const runs = await listOptimizationRuns(latestBatch.id);
    latestRun = runs.find((r) => r.state === "SUCCEEDED") ?? runs[0] ?? null;
    if (latestRun) {
      const [planList, stressList, mergeList] = await Promise.all([
        listStrategyPlans(latestRun.id),
        listStressAssessments(latestRun.id),
        listMergeAssessments(latestRun.id),
      ]);
      plans = planList;
      stress = stressList;
      merges = mergeList;
    }
  }
  let coverage: CoverageInterval | null = null;
  if (latestRun) {
    coverage = extractCoverage(latestBatch, latestRun);
  }
  return {
    batches,
    latestBatch,
    latestBatchChildren,
    latestRun,
    plans,
    stress,
    merges,
    coverage,
  };
}

/**
 * Extracts the `CoverageInterval` published by the backend alongside the
 * run. We never recompute the partial-identification numbers on the
 * client: they are weighted aggregates that depend on the frozen scenario
 * set and the canonical random seed. If the run did not yet publish a
 * coverage record we surface null so the page renders an UNDEFINED state
 * instead of inventing numbers.
 */
function extractCoverage(
  _batch: SimulationBatchVersion | null,
  run: OptimizationRunVersion,
): CoverageInterval | null {
  const augmented = run as RunWithCoverage;
  return augmented.coverage ?? null;
}

/**
 * Helper type used by `extractCoverage` to read an optional `coverage`
 * field off the run response. The backend may attach this field once the
 * run reaches SUCCEEDED; we keep the type additive so the generated client
 * remains source-compatible with versions that do not yet expose it.
 */
export type RunWithCoverage = OptimizationRunVersion & {
  coverage?: CoverageInterval | null;
};
