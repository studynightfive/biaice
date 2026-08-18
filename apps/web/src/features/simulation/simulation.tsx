"use client";

import { useCallback, useEffect, useState } from "react";

import { PageFrame } from "@/components/shell/page-frame";
import { Button, EmptyState, Notice, StatusBadge, type StatusTone } from "@/components/ui";
import type {
  AwardMode,
  ObjectiveKind,
  OptimizationRun,
  SimulationBatch,
  StrategyPlan,
  StressAxis,
} from "@biaice/contracts";

import {
  cancelBatch,
  createBatch,
  createOptimizationRun,
  finalizeOptimizationRun,
  getCurrentIdentity,
  invalidateOptimizationRun,
  invalidateStrategyPlan,
  loadBaselineBundle,
  loadSimulationBundle,
  publishStrategyPlan,
  retryBatch,
  type BaselineBundle,
  type SimulationBundle,
} from "./api";
import styles from "./styles/feature-simulation.module.css";
import { useApiResource } from "./use-api-resource";

export interface SimulationProps {
  readonly unitId: string;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "请求失败，请稍后重试。";
}

function stateTone(state: string): StatusTone {
  if (new Set(["SUCCEEDED", "FINALIZED", "PUBLISHED", "PASS"]).has(state)) return "success";
  if (new Set(["RUNNING", "PENDING", "DRAFT"]).has(state)) return "info";
  if (new Set(["INDETERMINATE", "FAILED_RETRYABLE"]).has(state)) return "warning";
  if (new Set(["FAILED", "FAILED_TERMINAL", "INVALIDATED", "FAIL"]).has(state)) {
    return "critical";
  }
  return "neutral";
}

export default function SimulationBlock({ unitId }: SimulationProps) {
  const loader = useCallback(async () => {
    const [bundle, baselineBundle, identity] = await Promise.all([
        loadSimulationBundle(unitId),
        loadBaselineBundle(unitId),
        getCurrentIdentity(),
      ]);
    return { bundle, baselineBundle, mfaVerified: identity.mfa_verified };
  }, [unitId]);
  const { data, error, refresh } = useApiResource(loader);
  const bundle = data?.bundle ?? null;
  const baselineBundle = data?.baselineBundle ?? null;
  const mfaVerified = data?.mfaVerified ?? false;

  useEffect(() => {
    const running =
      bundle?.latestBatch?.state === "RUNNING" || bundle?.latestRun?.state === "RUNNING";
    if (!running) return;
    const timer = window.setInterval(() => void refresh(), 5_000);
    return () => window.clearInterval(timer);
  }, [bundle?.latestBatch?.state, bundle?.latestRun?.state, refresh]);

  return (
    <PageFrame
      title="仿真与方案"
      eyebrow="FR-07 / FR-08"
      description="运行批次、静态校验、场景评估、优化、压力测试与方案发布均使用同一冻结输入链。"
    >
      {error ? <Notice tone="danger" title="无法读取仿真数据">{errorMessage(error)}</Notice> : null}
      {!bundle && !error ? <Notice tone="info" title="正在加载">正在读取最新批次与优化结果。</Notice> : null}
      {bundle && baselineBundle ? (
        <>
          <StatusSummary bundle={bundle} />
          {!mfaVerified ? (
            <Notice tone="warning" title="需要 MFA 验证">
              当前会话可浏览结果，但创建、取消、重试、定稿和发布操作会被禁用。
            </Notice>
          ) : null}
          <BatchSection
            unitId={unitId}
            bundle={bundle}
            baselineBundle={baselineBundle}
            mfaVerified={mfaVerified}
            onChanged={refresh}
          />
          <ResultSections bundle={bundle} />
          <OptimizationSection
            bundle={bundle}
            mfaVerified={mfaVerified}
            onChanged={refresh}
          />
        </>
      ) : null}
    </PageFrame>
  );
}

function StatusSummary({ bundle }: { readonly bundle: SimulationBundle }) {
  return (
    <div className={styles.readinessBar} role="status">
      <SummaryField label="最新批次" value={bundle.latestBatch?.state ?? "NONE"} />
      <SummaryField label="最新优化" value={bundle.latestRun?.state ?? "NONE"} />
      <SummaryField label="方案数量" value={String(bundle.plans.length)} />
      <SummaryField label="压力轴" value={String(bundle.stress.length)} />
    </div>
  );
}

function SummaryField({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={styles.fieldValue}>{value}</span>
    </div>
  );
}

function BatchSection({
  unitId,
  bundle,
  baselineBundle,
  mfaVerified,
  onChanged,
}: {
  readonly unitId: string;
  readonly bundle: SimulationBundle;
  readonly baselineBundle: BaselineBundle;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  return (
    <section className={styles.block} aria-label="simulation-batches">
      <h2 className={styles.blockTitle}>仿真批次</h2>
      {bundle.batches.length === 0 ? (
        <EmptyState title="尚无批次" description="需要冻结基线与场景集后才能创建。" />
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>batch_id</th>
              <th>state</th>
              <th>award_mode</th>
              <th>progress</th>
              <th>updated</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {bundle.batches.map((batch) => (
              <BatchRow
                key={batch.batch_id}
                batch={batch}
                mfaVerified={mfaVerified}
                onChanged={onChanged}
              />
            ))}
          </tbody>
        </table>
      )}
      <CreateBatchForm
        unitId={unitId}
        baselineBundle={baselineBundle}
        disabled={!mfaVerified || bundle.batches.some((batch) => batch.state === "RUNNING")}
        onChanged={onChanged}
      />
    </section>
  );
}

function BatchRow({
  batch,
  mfaVerified,
  onChanged,
}: {
  readonly batch: SimulationBatch;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  async function run(action: "cancel" | "retry") {
    setPending(true);
    try {
      if (action === "cancel") await cancelBatch(batch.batch_id);
      else await retryBatch(batch.batch_id);
      await onChanged();
    } finally {
      setPending(false);
    }
  }
  const canCancel = new Set(["PENDING", "RUNNING"]).has(batch.state);
  const canRetry = batch.state === "FAILED_RETRYABLE";
  return (
    <tr className={styles.tableRow}>
      <td>{batch.batch_id}</td>
      <td><StatusBadge tone={stateTone(batch.state)}>{batch.state}</StatusBadge></td>
      <td>{batch.award_mode}</td>
      <td>{batch.progress_percent ?? 0}%</td>
      <td>{batch.last_updated_at}</td>
      <td>
        <div className={styles.actions}>
          {canCancel ? (
            <Button variant="quiet" disabled={!mfaVerified || pending} onClick={() => void run("cancel")}>
              取消
            </Button>
          ) : null}
          {canRetry ? (
            <Button variant="secondary" disabled={!mfaVerified || pending} onClick={() => void run("retry")}>
              重试
            </Button>
          ) : null}
        </div>
      </td>
    </tr>
  );
}

function CreateBatchForm({
  unitId,
  baselineBundle,
  disabled,
  onChanged,
}: {
  readonly unitId: string;
  readonly baselineBundle: BaselineBundle;
  readonly disabled: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [awardMode, setAwardMode] = useState<AwardMode>("SINGLE");
  const [threshold, setThreshold] = useState("0.5");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scenarioSet = baselineBundle.scenarioSets.find((item) => item.state === "FROZEN") ?? null;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!baselineBundle.current || !scenarioSet) return;
    setPending(true);
    setError(null);
    try {
      await createBatch(unitId, {
        decision_unit_id: unitId,
        baseline_id: baselineBundle.current.baseline_id,
        scenario_set_id: scenarioSet.scenario_set_id,
        award_mode: awardMode,
        policy_threshold: threshold,
      });
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={`${styles.modalPanel} ${styles.gapMd}`} onSubmit={submit}>
      <h3>创建批次</h3>
      <label>
        授标模式
        <select value={awardMode} onChange={(event) => setAwardMode(event.target.value as AwardMode)}>
          <option value="SINGLE">SINGLE</option>
          <option value="MULTI">MULTI</option>
          <option value="NONE">NONE</option>
        </select>
      </label>
      <label>
        策略阈值
        <input value={threshold} onChange={(event) => setThreshold(event.target.value)} required />
      </label>
      {error ? <Notice tone="danger" title="创建失败">{error}</Notice> : null}
      <Button
        type="submit"
        disabled={disabled || pending || !baselineBundle.current || !scenarioSet}
      >
        {pending ? "提交中…" : "创建仿真批次"}
      </Button>
    </form>
  );
}

function ResultSections({ bundle }: { readonly bundle: SimulationBundle }) {
  const children = bundle.latestBatchChildren;
  if (!children) return null;
  return (
    <>
      <SimpleTable
        title="候选策略"
        headers={["label", "expected_cost", "expected_margin"]}
        rows={children.candidates.map((candidate) => [
          candidate.label,
          candidate.expected_cost.value,
          candidate.expected_margin.value,
        ])}
      />
      <SimpleTable
        title="静态校验"
        headers={["candidate_id", "status", "rule_codes", "detail"]}
        rows={children.staticValidations.map((item) => [
          item.candidate_id,
          item.status,
          item.rule_codes?.join(", ") || "—",
          item.detail ?? "—",
        ])}
      />
      <SimpleTable
        title="场景结果"
        headers={["candidate_id", "scenario_id", "feasible", "p_win", "validity"]}
        rows={children.scenarioOutcomes.map((item) => [
          item.candidate_id,
          item.scenario_id,
          item.feasible ? "yes" : "no",
          item.p_win.value,
          item.review_validity,
        ])}
      />
      <SimpleTable
        title="场景策略评估"
        headers={["candidate_id", "scenario_id", "validity", "recommended", "reason"]}
        rows={children.scenarioAssessments.map((item) => [
          item.candidate_id,
          item.scenario_id,
          item.review_validity,
          item.recommended ? "yes" : "no",
          item.reason_code,
        ])}
      />
    </>
  );
}

function SimpleTable({
  title,
  headers,
  rows,
}: {
  readonly title: string;
  readonly headers: ReadonlyArray<string>;
  readonly rows: ReadonlyArray<ReadonlyArray<React.ReactNode>>;
}) {
  return (
    <section className={styles.block}>
      <h2 className={styles.blockTitle}>{title}</h2>
      {rows.length === 0 ? (
        <EmptyState title="暂无结果" description="后端尚未产生该类记录。" />
      ) : (
        <table className={styles.table}>
          <thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className={styles.tableRow}>
                {row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function OptimizationSection({
  bundle,
  mfaVerified,
  onChanged,
}: {
  readonly bundle: SimulationBundle;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  return (
    <>
      <section className={styles.block} aria-label="optimization-run">
        <h2 className={styles.blockTitle}>优化运行</h2>
        {bundle.latestRun ? (
          <OptimizationRunDetails run={bundle.latestRun} mfaVerified={mfaVerified} onChanged={onChanged} />
        ) : (
          <EmptyState title="尚无优化运行" description="批次成功后可创建优化运行。" />
        )}
        <CreateOptimizationForm
          batch={bundle.latestBatch}
          disabled={!mfaVerified || bundle.latestBatch?.state !== "SUCCEEDED"}
          onChanged={onChanged}
        />
      </section>
      <PlanSection plans={bundle.plans} mfaVerified={mfaVerified} onChanged={onChanged} />
      <SimpleTable
        title="压力测试"
        headers={["axis", "passed", "weight", "detail"]}
        rows={bundle.stress.map((item) => [
          item.axis,
          item.passed ? "PASS" : "FAIL",
          item.stress_weight.value,
          item.detail,
        ])}
      />
      <SimpleTable
        title="合并评估"
        headers={["plan_id", "linkage", "accepted", "blocked_reason"]}
        rows={bundle.merges.map((item) => [
          item.plan_id,
          item.linkage,
          item.accepted ? "yes" : "no",
          item.blocked_reason_code ?? "—",
        ])}
      />
    </>
  );
}

function OptimizationRunDetails({
  run,
  mfaVerified,
  onChanged,
}: {
  readonly run: OptimizationRun;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  async function transition(action: "finalize" | "invalidate") {
    setPending(true);
    try {
      if (action === "finalize") await finalizeOptimizationRun(run.run_id);
      else await invalidateOptimizationRun(run.run_id);
      await onChanged();
    } finally {
      setPending(false);
    }
  }
  return (
    <div className={styles.blockGrid}>
      <SummaryField label="run_id" value={run.run_id} />
      <SummaryField label="state" value={run.state} />
      <SummaryField label="objective" value={run.objective_kind} />
      <SummaryField label="progress" value={`${run.progress_percent ?? 0}%`} />
      <div className={styles.actions}>
        {run.state === "SUCCEEDED" ? (
          <Button disabled={!mfaVerified || pending} onClick={() => void transition("finalize")}>定稿</Button>
        ) : null}
        {!new Set(["INVALIDATED", "FINALIZED"]).has(run.state) ? (
          <Button variant="quiet" disabled={!mfaVerified || pending} onClick={() => void transition("invalidate")}>失效</Button>
        ) : null}
      </div>
    </div>
  );
}

function CreateOptimizationForm({
  batch,
  disabled,
  onChanged,
}: {
  readonly batch: SimulationBatch | null;
  readonly disabled: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [objective, setObjective] = useState<ObjectiveKind>("COST_MIN");
  const [axis, setAxis] = useState<StressAxis>("PRICE_BAND");
  const [label, setLabel] = useState("Candidate A");
  const [cost, setCost] = useState("0");
  const [margin, setMargin] = useState("0");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!batch) return;
    setPending(true);
    setError(null);
    try {
      await createOptimizationRun(batch.batch_id, {
        objective_kind: objective,
        award_mode: batch.award_mode,
        policy_threshold: batch.policy_threshold.value,
        blueprints: [{ label, expected_cost: cost, expected_margin: margin }],
        stress_axes: [axis],
      });
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }
  return (
    <form className={`${styles.modalPanel} ${styles.gapMd}`} onSubmit={submit}>
      <h3>创建优化运行</h3>
      <label>目标
        <select value={objective} onChange={(event) => setObjective(event.target.value as ObjectiveKind)}>
          <option value="COST_MIN">COST_MIN</option><option value="MARGIN_MAX">MARGIN_MAX</option>
          <option value="COVERAGE_MAX">COVERAGE_MAX</option><option value="RISK_MIN">RISK_MIN</option>
        </select>
      </label>
      <label>压力轴
        <select value={axis} onChange={(event) => setAxis(event.target.value as StressAxis)}>
          <option value="PRICE_BAND">PRICE_BAND</option><option value="TIMING">TIMING</option>
          <option value="COMPLIANCE">COMPLIANCE</option><option value="PROVIDER_OUTAGE">PROVIDER_OUTAGE</option>
          <option value="UNIT_FAILURE">UNIT_FAILURE</option>
        </select>
      </label>
      <label>候选名称<input value={label} onChange={(event) => setLabel(event.target.value)} required /></label>
      <label>预计成本<input value={cost} onChange={(event) => setCost(event.target.value)} required /></label>
      <label>预计利润<input value={margin} onChange={(event) => setMargin(event.target.value)} required /></label>
      {error ? <Notice tone="danger" title="创建失败">{error}</Notice> : null}
      <Button type="submit" disabled={disabled || pending}>{pending ? "提交中…" : "创建优化运行"}</Button>
    </form>
  );
}

function PlanSection({
  plans,
  mfaVerified,
  onChanged,
}: {
  readonly plans: ReadonlyArray<StrategyPlan>;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  return (
    <section className={styles.block}>
      <h2 className={styles.blockTitle}>策略方案</h2>
      {plans.length === 0 ? <EmptyState title="暂无方案" description="优化运行尚未产生方案。" /> : (
        <table className={styles.table}>
          <thead><tr><th>plan_id</th><th>state</th><th>objective</th><th>coverage</th><th>操作</th></tr></thead>
          <tbody>{plans.map((plan) => <PlanRow key={plan.plan_id} plan={plan} mfaVerified={mfaVerified} onChanged={onChanged} />)}</tbody>
        </table>
      )}
    </section>
  );
}

function PlanRow({
  plan,
  mfaVerified,
  onChanged,
}: {
  readonly plan: StrategyPlan;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  async function transition(action: "publish" | "invalidate") {
    setPending(true);
    try {
      if (action === "publish") await publishStrategyPlan(plan.plan_id);
      else await invalidateStrategyPlan(plan.plan_id);
      await onChanged();
    } finally {
      setPending(false);
    }
  }
  return (
    <tr className={styles.tableRow}>
      <td>{plan.plan_id}</td><td>{plan.state}</td><td>{plan.objective_kind}</td><td>{plan.coverage.value}</td>
      <td><div className={styles.actions}>
        {plan.state === "DRAFT" ? <Button disabled={!mfaVerified || pending} onClick={() => void transition("publish")}>发布</Button> : null}
        {plan.state !== "INVALIDATED" ? <Button variant="quiet" disabled={!mfaVerified || pending} onClick={() => void transition("invalidate")}>失效</Button> : null}
      </div></td>
    </tr>
  );
}
