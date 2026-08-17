/**
 * Compile-time type tests for the simulation feature's exported types.
 *
 * These assertions are checked by `tsd` (or by `tsc --noEmit` in CI). They
 * exist so the page block cannot accidentally rename a field that the
 * backend contract depends on, and so that refactors across the feature
 * surface a clear error rather than silently regressing.
 */

import { expectType, expectError } from "tsd";

import type {
  DecisionBaselineVersion,
  ScenarioSetVersion,
  SimulationBatchVersion,
  OptimizationRunVersion,
  StrategyPlanVersion,
  RecommendationEligibilityVersion,
  SimulationAssessmentSnapshot,
  CoverageInterval,
  MoneyAmount,
  Models,
} from "../types";

/* -------------------------------------------------------------------------- */
/*  DecisionBaselineVersion shape                                             */
/* -------------------------------------------------------------------------- */

declare const baseline: DecisionBaselineVersion;
expectType<string>(baseline.frozen_rule_set_version);
expectType<string>(baseline.frozen_response_profile_version);
expectType<string>(baseline.frozen_cost_baseline_version);
expectType<string>(baseline.frozen_commercial_policy_version);
expectType<string>(baseline.frozen_model_artifact_version);
expectType<string>(baseline.input_manifest_hash);
expectType<string>(baseline.as_of);
expectType<boolean>(baseline.is_complete);
expectType<string[]>(baseline.frozen_competitor_profiles);
expectType<string[]>(baseline.frozen_market_priors);
expectType<string | null>(baseline.frozen_unknown_entrant_profile);

// DecisionBaselineVersion must extend VersionMeta, so version + id are present.
expectType<string>(baseline.id);
expectType<string>(baseline.version);

/* -------------------------------------------------------------------------- */
/*  ScenarioSetVersion shape                                                  */
/* -------------------------------------------------------------------------- */

declare const set: ScenarioSetVersion;
expectType<ScenarioSetVersion["probability_scenarios"]>(set.probability_scenarios);
expectType<ScenarioSetVersion["stress_scenarios"]>(set.stress_scenarios);
expectType<string>(set.random_seed);
expectType<string>(set.total_probability_weight);

/* -------------------------------------------------------------------------- */
/*  SimulationBatchVersion shape                                             */
/* -------------------------------------------------------------------------- */

declare const batch: SimulationBatchVersion;
expectType<SimulationBatchVersion["state"]>(batch.state);
expectType<SimulationBatchVersion["candidates"]>(batch.candidates);
expectType<SimulationBatchVersion["static_validations"]>(batch.static_validations);

/* -------------------------------------------------------------------------- */
/*  OptimizationRunVersion shape                                             */
/* -------------------------------------------------------------------------- */

declare const run: OptimizationRunVersion;
expectType<OptimizationRunVersion["state"]>(run.state);
expectType<OptimizationRunVersion["objective_bounds"]>(run.objective_bounds);

/* -------------------------------------------------------------------------- */
/*  StrategyPlanVersion shape                                                 */
/* -------------------------------------------------------------------------- */

declare const plan: StrategyPlanVersion;
expectType<StrategyPlanVersion["state"]>(plan.state);
expectType<StrategyPlanVersion["objective"]>(plan.objective);
expectType<boolean>(plan.proxy_mode);

/* -------------------------------------------------------------------------- */
/*  RecommendationEligibilityVersion shape                                    */
/* -------------------------------------------------------------------------- */

declare const eligibility: RecommendationEligibilityVersion;
expectType<RecommendationEligibilityVersion["state"]>(eligibility.state);
expectType<RecommendationEligibilityVersion["inputs"]>(eligibility.inputs);
expectType<string[]>(eligibility.blocking_reasons);
expectType<false>(eligibility.includes_commercial_approval);

/* -------------------------------------------------------------------------- */
/*  SimulationAssessmentSnapshot shape                                        */
/* -------------------------------------------------------------------------- */

declare const snapshot: SimulationAssessmentSnapshot;
expectType<SimulationAssessmentSnapshot["watermark"]>(snapshot.watermark);
expectType<boolean>(snapshot.is_latest);
expectType<string>(snapshot.payload_url);

/* -------------------------------------------------------------------------- */
/*  CoverageInterval & MoneyAmount                                            */
/* -------------------------------------------------------------------------- */

declare const coverage: CoverageInterval;
expectType<string | "UNDEFINED">(coverage.coverage);
expectType<number | "UNDEFINED">(coverage.n_eff);

declare const money: MoneyAmount;
expectType<string>(money.value);
expectType<string>(money.currency);

/* -------------------------------------------------------------------------- */
/*  Models namespace mirrors the generated client                             */
/* -------------------------------------------------------------------------- */

expectType<DecisionBaselineVersion>(null as unknown as Models["DecisionBaselineVersion"]);
expectType<ScenarioSetVersion>(null as unknown as Models["ScenarioSetVersion"]);

// The Models namespace must not export any unrelated resources.
expectError(() => Models["SomeRandomResource"]);
