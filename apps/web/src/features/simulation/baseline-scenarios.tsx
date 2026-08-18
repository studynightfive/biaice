"use client";

import { useCallback, useState } from "react";

import { PageFrame } from "@/components/shell/page-frame";
import { Button, EmptyState, Notice, StatusBadge } from "@/components/ui";
import type {
  CandidateSearchSpace,
  DecisionBaseline,
  ScenarioSet,
} from "@biaice/contracts";

import {
  createScenarioSet,
  createSearchSpace,
  getCurrentIdentity,
  loadBaselineBundle,
  type BaselineBundle,
} from "./api";
import { CopyHashButton } from "./components/copy-hash-button";
import styles from "./styles/feature-simulation.module.css";
import { useApiResource } from "./use-api-resource";

export interface BaselineScenariosProps {
  readonly unitId: string;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "请求失败，请稍后重试。";
}

export default function BaselineScenariosBlock({ unitId }: BaselineScenariosProps) {
  const loader = useCallback(async () => {
    const [bundle, identity] = await Promise.all([
        loadBaselineBundle(unitId),
        getCurrentIdentity(),
      ]);
    return { bundle, mfaVerified: identity.mfa_verified };
  }, [unitId]);
  const { data, error, refresh } = useApiResource(loader);
  const bundle = data?.bundle ?? null;
  const mfaVerified = data?.mfaVerified ?? false;

  return (
    <PageFrame
      title="决策基线与场景"
      eyebrow="FR-06"
      description="核对冻结的输入清单，并建立与该基线严格关联的搜索空间和场景集。"
    >
      {error ? (
        <Notice tone="danger" title="无法读取仿真基线">
          {errorMessage(error)}
        </Notice>
      ) : null}
      {!bundle && !error ? (
        <Notice tone="info" title="正在加载">
          正在读取最新基线、搜索空间和场景集。
        </Notice>
      ) : null}
      {bundle ? (
        <>
          <Summary bundle={bundle} />
          <BaselineSection current={bundle.current} superseded={bundle.superseded} />
          <SearchSpaceSection
            unitId={unitId}
            baseline={bundle.current}
            spaces={bundle.searchSpaces}
            mfaVerified={mfaVerified}
            onChanged={refresh}
          />
          <ScenarioSetSection
            unitId={unitId}
            baseline={bundle.current}
            spaces={bundle.searchSpaces}
            sets={bundle.scenarioSets}
            mfaVerified={mfaVerified}
            onChanged={refresh}
          />
        </>
      ) : null}
    </PageFrame>
  );
}

function Summary({ bundle }: { readonly bundle: BaselineBundle }) {
  return (
    <div className={styles.readinessBar} role="status">
      <SummaryField label="基线就绪状态" value={bundle.readiness.status} />
      <SummaryField label="搜索空间" value={String(bundle.searchSpaces.length)} />
      <SummaryField label="场景集" value={String(bundle.scenarioSets.length)} />
      <SummaryField
        label="阻塞原因"
        value={bundle.readiness.reasonCodes.join(", ") || "—"}
      />
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

function BaselineSection({
  current,
  superseded,
}: {
  readonly current: DecisionBaseline | null;
  readonly superseded: ReadonlyArray<DecisionBaseline>;
}) {
  return (
    <section className={styles.block} aria-label="decision-baseline">
      <h2 className={styles.blockTitle}>当前冻结基线</h2>
      {!current ? (
        <EmptyState
          title="尚无冻结基线"
          description="请先从已发布的上游版本生成输入清单并冻结决策基线。"
        />
      ) : (
        <div className={styles.blockGrid}>
          <Field label="baseline_id">{current.baseline_id}</Field>
          <Field label="version_id">{current.version_id}</Field>
          <Field label="state">
            <StatusBadge tone="success">{current.state}</StatusBadge>
          </Field>
          <Field label="frozen_at">{current.frozen_at ?? "—"}</Field>
          <Field label="manifest_id">{current.manifest.manifest_id}</Field>
          <Field label="manifest_hash">
            <span className={styles.hashMono}>
              {current.manifest.manifest_hash}
              <CopyHashButton
                value={current.manifest.manifest_hash}
                label="copy-manifest-hash"
              />
            </span>
          </Field>
          <Field label="manifest items">{String(current.manifest.items.length)}</Field>
          <Field label="created_at">{current.created_at}</Field>
        </div>
      )}
      {superseded.length > 0 ? (
        <table className={`${styles.table} ${styles.gapMd}`}>
          <thead>
            <tr>
              <th>baseline_id</th>
              <th>state</th>
              <th>created_at</th>
            </tr>
          </thead>
          <tbody>
            {superseded.map((baseline) => (
              <tr key={baseline.version_id} className={styles.tableRow}>
                <td>{baseline.baseline_id}</td>
                <td>{baseline.state}</td>
                <td>{baseline.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}

function SearchSpaceSection({
  unitId,
  baseline,
  spaces,
  mfaVerified,
  onChanged,
}: {
  readonly unitId: string;
  readonly baseline: DecisionBaseline | null;
  readonly spaces: ReadonlyArray<CandidateSearchSpace>;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const latest = spaces[0] ?? null;
  return (
    <section className={styles.block} aria-label="candidate-search-space">
      <h2 className={styles.blockTitle}>候选搜索空间</h2>
      {latest ? (
        <div className={styles.blockGrid}>
          <Field label="search_space_id">{latest.search_space_id}</Field>
          <Field label="state">{latest.state}</Field>
          <Field label="description">{latest.description}</Field>
          <Field label="dimension_axes">{latest.dimension_axes.join(", ")}</Field>
          <Field label="candidate lower bound">
            {String(latest.candidate_count_lower_bound)}
          </Field>
          <Field label="baseline_version_id">{latest.baseline_version_id}</Field>
        </div>
      ) : (
        <EmptyState title="尚无搜索空间" description="冻结基线后可建立第一个候选搜索空间。" />
      )}
      <SearchSpaceForm
        unitId={unitId}
        baseline={baseline}
        disabled={!mfaVerified}
        onChanged={onChanged}
      />
    </section>
  );
}

function SearchSpaceForm({
  unitId,
  baseline,
  disabled,
  onChanged,
}: {
  readonly unitId: string;
  readonly baseline: DecisionBaseline | null;
  readonly disabled: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [description, setDescription] = useState("价格与质量候选维度");
  const [axes, setAxes] = useState("price, quality");
  const [candidateCount, setCandidateCount] = useState(2);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!baseline) return;
    setPending(true);
    setError(null);
    try {
      const dimensionAxes = [...new Set(axes.split(",").map((axis) => axis.trim()).filter(Boolean))];
      await createSearchSpace(unitId, {
        decision_unit_id: unitId,
        baseline_id: baseline.baseline_id,
        description,
        dimension_axes: dimensionAxes,
        candidate_count_lower_bound: candidateCount,
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
      <h3>建立搜索空间</h3>
      <label>
        描述
        <input value={description} onChange={(event) => setDescription(event.target.value)} required />
      </label>
      <label>
        维度（逗号分隔）
        <input value={axes} onChange={(event) => setAxes(event.target.value)} required />
      </label>
      <label>
        最少候选数
        <input
          type="number"
          min={1}
          value={candidateCount}
          onChange={(event) => setCandidateCount(Number(event.target.value))}
          required
        />
      </label>
      {error ? <Notice tone="danger" title="创建失败">{error}</Notice> : null}
      <Button type="submit" disabled={!baseline || disabled || pending}>
        {pending ? "提交中…" : "创建并冻结"}
      </Button>
      {disabled ? <p className={styles.caption}>此操作需要 MFA 验证。</p> : null}
    </form>
  );
}

function ScenarioSetSection({
  unitId,
  baseline,
  spaces,
  sets,
  mfaVerified,
  onChanged,
}: {
  readonly unitId: string;
  readonly baseline: DecisionBaseline | null;
  readonly spaces: ReadonlyArray<CandidateSearchSpace>;
  readonly sets: ReadonlyArray<ScenarioSet>;
  readonly mfaVerified: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const latest = sets[0] ?? null;
  const frozenSpace = spaces.find((space) => space.state === "FROZEN") ?? null;
  return (
    <section className={styles.block} aria-label="scenario-set">
      <h2 className={styles.blockTitle}>场景集</h2>
      {latest ? (
        <>
          <div className={styles.blockGrid}>
            <Field label="scenario_set_id">{latest.scenario_set_id}</Field>
            <Field label="state">{latest.state}</Field>
            <Field label="search_space_version_id">{latest.search_space_version_id}</Field>
            <Field label="stress_axes">{latest.stress_axes.join(", ") || "—"}</Field>
          </div>
          <table className={`${styles.table} ${styles.gapMd}`}>
            <thead>
              <tr>
                <th>kind</th>
                <th>label</th>
                <th>weight</th>
              </tr>
            </thead>
            <tbody>
              {latest.members.map((member) => (
                <tr key={member.scenario_id} className={styles.tableRow}>
                  <td>{member.scenario_kind}</td>
                  <td>{member.label}</td>
                  <td>{member.weight.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <EmptyState title="尚无场景集" description="搜索空间冻结后可建立搜索与评估场景。" />
      )}
      <ScenarioSetForm
        unitId={unitId}
        baseline={baseline}
        searchSpace={frozenSpace}
        disabled={!mfaVerified}
        onChanged={onChanged}
      />
    </section>
  );
}

function ScenarioSetForm({
  unitId,
  baseline,
  searchSpace,
  disabled,
  onChanged,
}: {
  readonly unitId: string;
  readonly baseline: DecisionBaseline | null;
  readonly searchSpace: CandidateSearchSpace | null;
  readonly disabled: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!baseline || !searchSpace) return;
    setPending(true);
    setError(null);
    try {
      await createScenarioSet(unitId, {
        decision_unit_id: unitId,
        baseline_id: baseline.baseline_id,
        search_space_id: searchSpace.search_space_id,
        members: [
          {
            scenario_id: globalThis.crypto.randomUUID(),
            scenario_kind: "SEARCH",
            weight: "0.5",
            label: "Search scenario",
          },
          {
            scenario_id: globalThis.crypto.randomUUID(),
            scenario_kind: "EVALUATION",
            weight: "0.5",
            label: "Evaluation scenario",
          },
        ],
        stress_axes: ["PRICE_BAND"],
      });
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={`${styles.actions} ${styles.gapMd}`}>
      <Button
        type="button"
        onClick={() => void submit()}
        disabled={!baseline || !searchSpace || disabled || pending}
      >
        {pending ? "提交中…" : "创建标准场景集"}
      </Button>
      {error ? <Notice tone="danger" title="创建失败">{error}</Notice> : null}
    </div>
  );
}

function Field({ label, children }: { readonly label: string; readonly children: React.ReactNode }) {
  return (
    <div className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={styles.fieldValue}>{children}</span>
    </div>
  );
}
