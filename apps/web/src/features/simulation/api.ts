/** Contract-aligned browser data layer for the simulation feature. */

import { getBiaiceClient, type BiaiceClient } from "@/lib/api/client";
import type {
  CandidateListResponse,
  CandidateSearchSpace,
  CreateBatchRequest,
  CreateOptimizationRunRequest,
  CreateScenarioSetRequest,
  CreateSearchSpaceRequest,
  DecisionBaseline,
  FreezeBaselineRequest,
  MeResponse,
  MergeAssessment,
  OptimizationRun,
  RecommendationEligibility,
  RecommendationEligibilityRequest,
  ScenarioOutcome,
  ScenarioSet,
  ScenarioStrategyAssessment,
  SimulationAssessmentSnapshot,
  SimulationBatch,
  SnapshotDownloadResponse,
  SnapshotRequest,
  StaticCandidateValidation,
  StrategyPlan,
  StressTestAssessment,
} from "@biaice/contracts";

import { deriveBaselineReadiness, type BaselineReadiness, type Uuid } from "./types";

const NO_STORE: RequestCache = "no-store";
const NEXT_REVALIDATE = { revalidate: 0 } as const;

function apiClient(): BiaiceClient {
  return getBiaiceClient();
}

function readOnly() {
  return { cache: NO_STORE, next: NEXT_REVALIDATE };
}

function writeOptions(action: string, resourceId: string, idempotencyKey?: string) {
  return {
    cache: NO_STORE,
    next: NEXT_REVALIDATE,
    idempotencyKey: idempotencyKey ?? newIdempotencyKey(action, resourceId),
  };
}

function segment(value: string): string {
  return encodeURIComponent(value);
}

async function listItems<T>(path: string): Promise<T[]> {
  const response = await apiClient().request<{ readonly items: ReadonlyArray<T> }>(
    "GET",
    path,
    readOnly(),
  );
  return [...response.items];
}

export function newIdempotencyKey(action: string, hint?: string): string {
  const suffix = hint ? `:${hint}` : "";
  return `${action}:${globalThis.crypto.randomUUID()}${suffix}`;
}

export function getCurrentIdentity(): Promise<MeResponse> {
  return apiClient().request<MeResponse>("GET", "/api/v1/me", readOnly());
}

export function listDecisionBaselines(unitId: Uuid): Promise<DecisionBaseline[]> {
  return listItems(`/api/v1/decision-units/${segment(unitId)}/decision-baselines`);
}

export function getDecisionBaseline(baselineId: Uuid): Promise<DecisionBaseline> {
  return apiClient().request<DecisionBaseline>(
    "GET",
    `/api/v1/decision-baselines/${segment(baselineId)}`,
    readOnly(),
  );
}

export function freezeDecisionBaseline(
  unitId: Uuid,
  body: FreezeBaselineRequest,
  idempotencyKey?: string,
): Promise<DecisionBaseline> {
  return apiClient().request<DecisionBaseline>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/decision-baselines/freeze`,
    {
      ...writeOptions("freeze_decision_baseline", unitId, idempotencyKey),
      body,
    },
  );
}

export function listSearchSpaces(unitId: Uuid): Promise<CandidateSearchSpace[]> {
  return listItems(`/api/v1/decision-units/${segment(unitId)}/candidate-search-spaces`);
}

export function createSearchSpace(
  unitId: Uuid,
  body: CreateSearchSpaceRequest,
  idempotencyKey?: string,
): Promise<CandidateSearchSpace> {
  return apiClient().request<CandidateSearchSpace>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/candidate-search-spaces`,
    {
      ...writeOptions("create_candidate_search_space", unitId, idempotencyKey),
      body,
    },
  );
}

export function listScenarioSets(unitId: Uuid): Promise<ScenarioSet[]> {
  return listItems(`/api/v1/decision-units/${segment(unitId)}/scenario-sets`);
}

export function createScenarioSet(
  unitId: Uuid,
  body: CreateScenarioSetRequest,
  idempotencyKey?: string,
): Promise<ScenarioSet> {
  return apiClient().request<ScenarioSet>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/scenario-sets`,
    {
      ...writeOptions("create_scenario_set", unitId, idempotencyKey),
      body,
    },
  );
}

export function getScenarioSet(scenarioSetId: Uuid): Promise<ScenarioSet> {
  return apiClient().request<ScenarioSet>(
    "GET",
    `/api/v1/scenario-sets/${segment(scenarioSetId)}`,
    readOnly(),
  );
}

export function freezeScenarioSet(
  scenarioSetId: Uuid,
  idempotencyKey?: string,
): Promise<ScenarioSet> {
  return apiClient().request<ScenarioSet>(
    "POST",
    `/api/v1/scenario-sets/${segment(scenarioSetId)}/freeze`,
    writeOptions("freeze_scenario_set", scenarioSetId, idempotencyKey),
  );
}

export function listBatches(unitId: Uuid): Promise<SimulationBatch[]> {
  return listItems(`/api/v1/decision-units/${segment(unitId)}/simulation-batches`);
}

export function getBatch(batchId: Uuid): Promise<SimulationBatch> {
  return apiClient().request<SimulationBatch>(
    "GET",
    `/api/v1/simulation-batches/${segment(batchId)}`,
    readOnly(),
  );
}

export function createBatch(
  unitId: Uuid,
  body: CreateBatchRequest,
  idempotencyKey?: string,
): Promise<SimulationBatch> {
  return apiClient().request<SimulationBatch>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/simulation-batches`,
    {
      ...writeOptions("create_simulation_batch", unitId, idempotencyKey),
      body,
    },
  );
}

export function cancelBatch(
  batchId: Uuid,
  idempotencyKey?: string,
): Promise<SimulationBatch> {
  return apiClient().request<SimulationBatch>(
    "POST",
    `/api/v1/simulation-batches/${segment(batchId)}/cancel`,
    writeOptions("cancel_simulation_batch", batchId, idempotencyKey),
  );
}

export function retryBatch(
  batchId: Uuid,
  idempotencyKey?: string,
): Promise<SimulationBatch> {
  return apiClient().request<SimulationBatch>(
    "POST",
    `/api/v1/simulation-batches/${segment(batchId)}/retry`,
    writeOptions("retry_simulation_batch", batchId, idempotencyKey),
  );
}

export interface BatchChildren {
  readonly candidates: SimulationCandidateList;
  readonly staticValidations: StaticCandidateValidation[];
  readonly scenarioOutcomes: ScenarioOutcome[];
  readonly scenarioAssessments: ScenarioStrategyAssessment[];
}

type SimulationCandidateList = CandidateListResponse["items"] extends ReadonlyArray<infer T>
  ? T[]
  : never;

export async function listBatchChildren(batchId: Uuid): Promise<BatchChildren> {
  const base = `/api/v1/simulation-batches/${segment(batchId)}`;
  const [candidates, staticValidations, scenarioOutcomes, scenarioAssessments] =
    await Promise.all([
      listItems<SimulationCandidateList[number]>(`${base}/candidates`),
      listItems<StaticCandidateValidation>(`${base}/static-validations`),
      listItems<ScenarioOutcome>(`${base}/scenario-outcomes`),
      listItems<ScenarioStrategyAssessment>(`${base}/scenario-assessments`),
    ]);
  return { candidates, staticValidations, scenarioOutcomes, scenarioAssessments };
}

export function listOptimizationRuns(batchId: Uuid): Promise<OptimizationRun[]> {
  return listItems(`/api/v1/simulation-batches/${segment(batchId)}/optimization-runs`);
}

export function getOptimizationRun(runId: Uuid): Promise<OptimizationRun> {
  return apiClient().request<OptimizationRun>(
    "GET",
    `/api/v1/optimization-runs/${segment(runId)}`,
    readOnly(),
  );
}

export function createOptimizationRun(
  batchId: Uuid,
  body: CreateOptimizationRunRequest,
  idempotencyKey?: string,
): Promise<OptimizationRun> {
  return apiClient().request<OptimizationRun>(
    "POST",
    `/api/v1/simulation-batches/${segment(batchId)}/optimization-runs`,
    {
      ...writeOptions("create_optimization_run", batchId, idempotencyKey),
      body,
    },
  );
}

export function finalizeOptimizationRun(
  runId: Uuid,
  idempotencyKey?: string,
): Promise<OptimizationRun> {
  return apiClient().request<OptimizationRun>(
    "POST",
    `/api/v1/optimization-runs/${segment(runId)}/finalize`,
    writeOptions("finalize_optimization_run", runId, idempotencyKey),
  );
}

export function invalidateOptimizationRun(
  runId: Uuid,
  idempotencyKey?: string,
): Promise<OptimizationRun> {
  return apiClient().request<OptimizationRun>(
    "POST",
    `/api/v1/optimization-runs/${segment(runId)}/invalidate`,
    writeOptions("invalidate_optimization_run", runId, idempotencyKey),
  );
}

export function listStrategyPlans(runId: Uuid): Promise<StrategyPlan[]> {
  return listItems(`/api/v1/optimization-runs/${segment(runId)}/strategy-plans`);
}

export function listStressAssessments(runId: Uuid): Promise<StressTestAssessment[]> {
  return listItems(
    `/api/v1/optimization-runs/${segment(runId)}/stress-test-assessments`,
  );
}

export function listMergeAssessments(runId: Uuid): Promise<MergeAssessment[]> {
  return listItems(`/api/v1/optimization-runs/${segment(runId)}/merge-assessments`);
}

export function publishStrategyPlan(
  planId: Uuid,
  idempotencyKey?: string,
): Promise<StrategyPlan> {
  return apiClient().request<StrategyPlan>(
    "POST",
    `/api/v1/strategy-plans/${segment(planId)}/publish`,
    writeOptions("publish_strategy_plan", planId, idempotencyKey),
  );
}

export function invalidateStrategyPlan(
  planId: Uuid,
  idempotencyKey?: string,
): Promise<StrategyPlan> {
  return apiClient().request<StrategyPlan>(
    "POST",
    `/api/v1/strategy-plans/${segment(planId)}/invalidate`,
    writeOptions("invalidate_strategy_plan", planId, idempotencyKey),
  );
}

export function listEligibilities(unitId: Uuid): Promise<RecommendationEligibility[]> {
  return listItems(
    `/api/v1/decision-units/${segment(unitId)}/recommendation-eligibilities`,
  );
}

export function getEligibility(eligibilityId: Uuid): Promise<RecommendationEligibility> {
  return apiClient().request<RecommendationEligibility>(
    "GET",
    `/api/v1/recommendation-eligibilities/${segment(eligibilityId)}`,
    readOnly(),
  );
}

export function createRecommendationEligibility(
  unitId: Uuid,
  body: RecommendationEligibilityRequest,
  idempotencyKey?: string,
): Promise<RecommendationEligibility> {
  return apiClient().request<RecommendationEligibility>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/recommendation-eligibilities`,
    {
      ...writeOptions("create_recommendation_eligibility", unitId, idempotencyKey),
      body,
    },
  );
}

export function listSnapshots(unitId: Uuid): Promise<SimulationAssessmentSnapshot[]> {
  return listItems(
    `/api/v1/decision-units/${segment(unitId)}/simulation-assessment-snapshots`,
  );
}

export function getSnapshot(snapshotId: Uuid): Promise<SimulationAssessmentSnapshot> {
  return apiClient().request<SimulationAssessmentSnapshot>(
    "GET",
    `/api/v1/simulation-assessment-snapshots/${segment(snapshotId)}`,
    readOnly(),
  );
}

export function createSnapshot(
  unitId: Uuid,
  body: SnapshotRequest,
  idempotencyKey?: string,
): Promise<SimulationAssessmentSnapshot> {
  return apiClient().request<SimulationAssessmentSnapshot>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/simulation-assessment-snapshots`,
    {
      ...writeOptions("create_simulation_assessment_snapshot", unitId, idempotencyKey),
      body,
    },
  );
}

export function downloadSnapshot(snapshotId: Uuid): Promise<SnapshotDownloadResponse> {
  return apiClient().request<SnapshotDownloadResponse>(
    "GET",
    `/api/v1/simulation-assessment-snapshots/${segment(snapshotId)}/download`,
    readOnly(),
  );
}

export interface BaselineBundle {
  readonly current: DecisionBaseline | null;
  readonly superseded: DecisionBaseline[];
  readonly searchSpaces: CandidateSearchSpace[];
  readonly scenarioSets: ScenarioSet[];
  readonly readiness: BaselineReadiness;
}

export async function loadBaselineBundle(unitId: Uuid): Promise<BaselineBundle> {
  const [baselines, searchSpaces, scenarioSets] = await Promise.all([
    listDecisionBaselines(unitId),
    listSearchSpaces(unitId),
    listScenarioSets(unitId),
  ]);
  const current = baselines.find((baseline) => baseline.state === "FROZEN") ?? null;
  const superseded = baselines.filter((baseline) => baseline !== current);
  return {
    current,
    superseded,
    searchSpaces,
    scenarioSets,
    readiness: deriveBaselineReadiness(current),
  };
}

export interface SimulationBundle {
  readonly batches: SimulationBatch[];
  readonly latestBatch: SimulationBatch | null;
  readonly latestBatchChildren: BatchChildren | null;
  readonly latestRun: OptimizationRun | null;
  readonly plans: StrategyPlan[];
  readonly stress: StressTestAssessment[];
  readonly merges: MergeAssessment[];
}

export async function loadSimulationBundle(unitId: Uuid): Promise<SimulationBundle> {
  const batches = await listBatches(unitId);
  const latestBatch =
    batches.find((batch) => batch.state === "SUCCEEDED") ?? batches[0] ?? null;
  if (!latestBatch) {
    return {
      batches,
      latestBatch: null,
      latestBatchChildren: null,
      latestRun: null,
      plans: [],
      stress: [],
      merges: [],
    };
  }

  const [latestBatchChildren, runs] = await Promise.all([
    listBatchChildren(latestBatch.batch_id),
    listOptimizationRuns(latestBatch.batch_id),
  ]);
  const latestRun =
    runs.find((run) => run.state === "FINALIZED" || run.state === "SUCCEEDED") ??
    runs[0] ??
    null;
  if (!latestRun) {
    return {
      batches,
      latestBatch,
      latestBatchChildren,
      latestRun: null,
      plans: [],
      stress: [],
      merges: [],
    };
  }

  const [plans, stress, merges] = await Promise.all([
    listStrategyPlans(latestRun.run_id),
    listStressAssessments(latestRun.run_id),
    listMergeAssessments(latestRun.run_id),
  ]);
  return {
    batches,
    latestBatch,
    latestBatchChildren,
    latestRun,
    plans,
    stress,
    merges,
  };
}
