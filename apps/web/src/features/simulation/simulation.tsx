/**
 * /simulation page block.
 *
 * Composition (top → bottom):
 *   1. Status bar with the latest BatchState, OptimizationRunState, PlanState
 *      and Coverage.
 *   2. Batch control: list of SimulationBatchVersion rows with expand.
 *   3. Static validation table (FR-07).
 *   4. Scenario results table (FR-07).
 *   5. Coverage & N_eff card (FR-08).
 *   6. Plan objective cards (FR-08).
 *   7. Stress axis chips (FR-08).
 *   8. Merge assessment list (FR-08).
 *
 * The block is a server component. Every fetch uses `no-store` cache
 * so the page always reflects the most recent backend state.
 */

import {
  Card,
  EmptyState,
  Notice,
  StatusBadge,
  type StatusTone,
} from "@/components/ui";
import { PageFrame } from "@/components/shell/page-frame";

import styles from "./styles/feature-simulation.module.css";

import { loadSimulationBundle, listEligibilities } from "./api";
import { CoverageCard } from "./components/coverage-card";
import { PlanObjectiveGrid } from "./components/plan-objective-card";
import { StressAxisGrid } from "./components/stress-axis-chip";
import { formatMoney } from "./format";
import type {
  BatchState,
  MergeAssessment,
  OptimizationRunVersion,
  PlanState,
  ScenarioAssessmentState,
  SimulationBatchVersion,
  StressTestAssessment,
} from "./types";

export interface SimulationProps {
  unitId: string;
  mfaVerified: boolean;
}

const BATCH_TONE: Record<BatchState, StatusTone> = {
  PENDING: "neutral",
  RUNNING: "info",
  SUCCEEDED: "success",
  FAILED: "critical",
  CANCELLED: "neutral",
  TIMED_OUT: "warning",
};

const PLAN_TONE: Record<PlanState, StatusTone> = {
  DRAFT: "neutral",
  FINALIZED: "info",
  PUBLISHED: "success",
  INVALIDATED: "critical",
};

const RUN_TONE: Record<OptimizationRunVersion["state"], StatusTone> = {
  PENDING: "neutral",
  RUNNING: "info",
  SUCCEEDED: "success",
  PARTIAL: "warning",
  FAILED: "critical",
  CANCELLED: "neutral",
};

const ASSESSMENT_TONE: Record<ScenarioAssessmentState, StatusTone> = {
  ASSESSED: "success",
  PARTIALLY_IDENTIFIED: "warning",
  INDETERMINATE: "neutral",
};

export default async function SimulationBlock({ unitId, mfaVerified }: SimulationProps) {
  const eligibilities = await listEligibilities(unitId);
  const latestEligibility = eligibilities[0] ?? null;
  const bundle = await loadSimulationBundle(unitId, latestEligibility);

  return (
    <PageFrame title="Simulation & strategy" eyebrow="member 6" description="Read-only view of the backend-owned batch, optimisation, stress and merge pipeline.">
      <StatusBar bundle={bundle} />
      {!mfaVerified ? (
        <Notice tone="warning" title="Multi-factor verification required">
          You can browse the simulation state, but freeze / cancel / retry / publish actions require an MFA-verified session.
        </Notice>
      ) : null}
      {bundle.latestBatch?.state === "FAILED" ? (
        <Notice tone="danger" title="Latest batch failed">
          {bundle.latestBatch.failure_reason ?? "The latest simulation batch failed; cancel/retry actions are disabled until upstream inputs are refrozen."}
        </Notice>
      ) : null}
      {bundle.latestBatch?.state === "RUNNING" ? (
        <Notice tone="info" title="Batch in progress">
          The latest batch is still RUNNING. The page revalidates on every navigation but never displays fabricated progress.
        </Notice>
      ) : null}
      <BatchSection bundle={bundle} unitId={unitId} mfaVerified={mfaVerified} />
      <StaticValidationSection bundle={bundle} />
      <ScenarioOutcomeSection bundle={bundle} />
      <CoverageSection bundle={bundle} />
      <PlanSection bundle={bundle} />
      <StressSection bundle={bundle} />
      <MergeSection bundle={bundle} />
    </PageFrame>
  );
}

function StatusBar({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  const batchState = bundle.latestBatch?.state ?? "NONE";
  const runState = bundle.latestRun?.state ?? "NONE";
  const planState: PlanState = bundle.plans[0]?.state ?? "DRAFT";
  const assessmentState =
    bundle.latestBatch && bundle.latestBatch.scenario_assessments.length > 0
      ? "ASSESSED"
      : "INDETERMINATE";
  return (
    <div className={styles.readinessBar} role="status" aria-live="polite">
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Batch</span>
          <span>
            <StatusBadge tone={batchState === "NONE" ? "neutral" : BATCH_TONE[batchState as BatchState]}>{batchState}</StatusBadge>
          </span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Latest run</span>
          <span>
            <StatusBadge tone={runState === "NONE" ? "neutral" : RUN_TONE[runState as OptimizationRunVersion["state"]]}>{runState}</StatusBadge>
          </span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Latest plan</span>
          <span>
            <StatusBadge tone={PLAN_TONE[planState]}>{planState}</StatusBadge>
          </span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Coverage</span>
          <span className={styles.fieldValue}>
            {bundle.coverage
              ? bundle.coverage.coverage === "UNDEFINED"
                ? "UNDEFINED"
                : String(bundle.coverage.coverage)
              : "UNDEFINED"}
          </span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Assessment state</span>
          <span>
            <StatusBadge tone={ASSESSMENT_TONE[assessmentState]}>{assessmentState}</StatusBadge>
          </span>
        </div>
      </Card>
    </div>
  );
}

function BatchSection({ bundle, unitId, mfaVerified }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>>; unitId: string; mfaVerified: boolean }) {
  const hasRunning = bundle.batches.some((b) => b.state === "RUNNING" || b.state === "PENDING");
  return (
    <section className={styles.block} aria-label="batch-control">
      <h2 className={styles.blockTitle}>Batch control</h2>
      {bundle.batches.length === 0 ? (
        <EmptyState
          title="No simulation batch yet"
          description={
            mfaVerified
              ? "Once the baseline is ready you can request the first batch from here."
              : "Sign in with multi-factor verification to request a new batch."
          }
        />
      ) : (
        <BatchTable batches={bundle.batches} batchChildren={bundle.latestBatchChildren} />
      )}
      <div className={styles.actions}>
        <CreateBatchIsland unitId={unitId} disabled={!mfaVerified || hasRunning} />
      </div>
    </section>
  );
}

function BatchTable({ batches, batchChildren }: { batches: SimulationBatchVersion[]; batchChildren: Awaited<ReturnType<typeof loadSimulationBundle>>["latestBatchChildren"] }) {
  return (
    <table className={styles.table} aria-label="batch-table">
      <thead>
        <tr>
          <th scope="col">batch_id</th>
          <th scope="col">state</th>
          <th scope="col">started_at</th>
          <th scope="col">completed_at</th>
          <th scope="col">job_id</th>
        </tr>
      </thead>
      <tbody>
        {batches.map((batch) => (
          <tr key={batch.id} className={styles.tableRow}>
            <td>{batch.id}</td>
            <td>
              <span className={styles.status + " " + (BATCH_TONE[batch.state] === "success" ? styles.statusIsOk : BATCH_TONE[batch.state] === "warning" ? styles.statusIsWarn : BATCH_TONE[batch.state] === "critical" ? styles.statusIsFail : styles.statusIsInfo)}>
                {batch.state}
              </span>
            </td>
            <td>{batch.started_at ?? "\u2014"}</td>
            <td>{batch.completed_at ?? "\u2014"}</td>
            <td>{batch.job_id ?? "\u2014"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StaticValidationSection({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  const rows = bundle.latestBatchChildren?.static_validations ?? [];
  if (rows.length === 0) {
    return (
      <section className={styles.block} aria-label="static-validation">
        <h2 className={styles.blockTitle}>Static validation</h2>
        <EmptyState title="No static validation rows" description="The latest batch has not published static validation results yet." />
      </section>
    );
  }
  return (
    <section className={styles.block} aria-label="static-validation">
      <h2 className={styles.blockTitle}>Static validation</h2>
      <table className={styles.table} aria-label="static-validation-table">
        <thead>
          <tr>
            <th scope="col">candidate</th>
            <th scope="col">commercial baseline</th>
            <th scope="col">reason</th>
            <th scope="col">rules</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.candidate_id} className={styles.tableRow + (row.baseline_commercial_passed ? "" : " " + styles.tableRowIsBlocked)}>
              <td>{row.candidate_id}</td>
              <td>
                <span className={styles.status + " " + (row.baseline_commercial_passed ? styles.statusIsOk : styles.statusIsFail)}>
                  {row.baseline_commercial_passed ? "PASS" : "FAIL"}
                </span>
              </td>
              <td>{row.baseline_commercial_reason_code ?? "\u2014"}</td>
              <td>
                <ul className={styles.reasonList}>
                  {row.rule_results.map((rule) => (
                    <li key={rule.rule_id} data-tone={rule.passed ? "info" : "fail"}>
                      {rule.rule_id} · {rule.passed ? "PASS" : "FAIL"}
                      {rule.reason_code ? " · " + rule.reason_code : ""}
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ScenarioOutcomeSection({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  const outcomes = bundle.latestBatchChildren?.scenario_outcomes ?? [];
  if (outcomes.length === 0) {
    return (
      <section className={styles.block} aria-label="scenario-outcomes">
        <h2 className={styles.blockTitle}>Scenario outcomes</h2>
        <EmptyState title="No scenario outcomes" description="The latest batch has not published scenario outcomes yet." />
      </section>
    );
  }
  return (
    <section className={styles.block} aria-label="scenario-outcomes">
      <h2 className={styles.blockTitle}>Scenario outcomes</h2>
      <table className={styles.table} aria-label="scenario-outcomes-table">
        <thead>
          <tr>
            <th scope="col">scenario</th>
            <th scope="col">candidate</th>
            <th scope="col">awardable</th>
            <th scope="col">eligible_for_award</th>
            <th scope="col">our_rank</th>
            <th scope="col">valid suppliers</th>
            <th scope="col">review validity</th>
            <th scope="col">results</th>
          </tr>
        </thead>
        <tbody>
          {outcomes.map((outcome) => (
            <tr key={outcome.outcome_id} className={styles.tableRow}>
              <td>{outcome.scenario_id}</td>
              <td>{outcome.candidate_id}</td>
              <td>{outcome.awardable ? "yes" : "no"}</td>
              <td>{outcome.eligible_for_award ? "yes" : "no"}</td>
              <td>{outcome.our_rank ?? "\u2014"}</td>
              <td>{outcome.valid_supplier_count}</td>
              <td>{outcome.review_validity}</td>
              <td>
                <ul className={styles.reasonList}>
                  {outcome.results.map((r, idx) => (
                    <li key={idx} data-tone={r.outcome === "AWARDED" ? "info" : r.outcome === "DISQUALIFIED" ? "warn" : "info"}>
                      {r.outcome} · rank {r.rank ?? "\u2014"} · {r.review_state}
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function CoverageSection({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  return (
    <section className={styles.block} aria-label="coverage">
      <h2 className={styles.blockTitle}>Coverage &amp; partial-identification interval</h2>
      <CoverageCard
        coverage={bundle.coverage}
        runId={bundle.latestRun?.id}
        basis={bundle.latestRun ? "evaluation set " + bundle.latestRun.evaluation_set_seed : undefined}
      />
    </section>
  );
}

function PlanSection({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  const plans = bundle.plans;
  const runId = bundle.latestRun?.id ?? "unknown";
  return (
    <section className={styles.block} aria-label="plan-objectives">
      <h2 className={styles.blockTitle}>Multi-objective plans</h2>
      {plans.length === 0 ? (
        <EmptyState
          title="No feasible plans"
          description={
            bundle.latestRun?.state === "FAILED"
              ? "Latest run failed; review the static validation block and the upstream baseline readiness before creating a new run."
              : "No plan has been published yet. The page never fabricates an objective value when the feasible set is empty."
          }
        />
      ) : (
        <PlanObjectiveGrid plans={plans} runId={runId} currency={bundle.latestBatch?.candidates?.[0]?.bid_value.currency} />
      )}
    </section>
  );
}

function StressSection({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  const axes: StressTestAssessment[] = bundle.stress;
  const currency = bundle.latestBatch?.candidates?.[0]?.bid_value.currency;
  return (
    <section className={styles.block} aria-label="stress-axes">
      <h2 className={styles.blockTitle}>Mandatory stress axes</h2>
      <StressAxisGrid axes={axes} currency={currency} />
      <p className={styles.caption + " " + styles.gapSm}>压力场景从不进入概率分母；只作为强制轴检查。</p>
    </section>
  );
}

function MergeSection({ bundle }: { bundle: Awaited<ReturnType<typeof loadSimulationBundle>> }) {
  const merges: MergeAssessment[] = bundle.merges;
  const blocked = merges.filter((m) => !m.merge_passed);
  return (
    <section className={styles.block} aria-label="merge-assessment">
      <h2 className={styles.blockTitle}>Merge assessment</h2>
      {merges.length === 0 ? (
        <EmptyState title="No merge clusters" description="The optimisation run has not produced any merge clusters yet." />
      ) : (
        <>
          {blocked.length > 0 ? (
            <Notice tone="warning" title="Chain-style merge blocked">
              {blocked.length} cluster(s) failed the complete-link condition. The optimizer never merges via
              transitive chains when any pair in the cluster violates the rule boundary.
            </Notice>
          ) : null}
          <table className={styles.table} aria-label="merge-table">
            <thead>
              <tr>
                <th scope="col">cluster</th>
                <th scope="col">candidates</th>
                <th scope="col">passed</th>
                <th scope="col">bid spread</th>
                <th scope="col">metric distance</th>
              </tr>
            </thead>
            <tbody>
              {merges.map((merge) => (
                <tr key={merge.cluster_id} className={styles.tableRow + (merge.merge_passed ? "" : " " + styles.tableRowIsBlocked)}>
                  <td>{merge.cluster_id}</td>
                  <td>{merge.candidate_ids.join(", ")}</td>
                  <td>
                    <span className={styles.status + " " + (merge.merge_passed ? styles.statusIsOk : styles.statusIsFail)}>
                      {merge.merge_passed ? "PASS" : "FAIL"}
                    </span>
                  </td>
                  <td>{merge.bid_spread ? formatMoney(merge.bid_spread, bundle.latestBatch?.candidates?.[0]?.bid_value.currency ?? "") : "\u2014"}</td>
                  <td>{merge.metric_distance ?? "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

async function CreateBatchIsland({ unitId, disabled }: { unitId: string; disabled: boolean }) {
  const mod = await import("./simulation.client");
  return <mod.CreateBatchButtonClient unitId={unitId} disabled={disabled} />;
}
