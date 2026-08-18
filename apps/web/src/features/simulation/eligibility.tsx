"use client";

import { useCallback, useState } from "react";

import { PageFrame } from "@/components/shell/page-frame";
import { Button, EmptyState, Notice, StatusBadge, type StatusTone } from "@/components/ui";
import type {
  DecisionBaseline,
  RecommendationEligibility,
  ReviewValidity,
  SimulationAssessmentSnapshot,
} from "@biaice/contracts";

import {
  createRecommendationEligibility,
  createSnapshot,
  downloadSnapshot,
  getCurrentIdentity,
  listDecisionBaselines,
  listEligibilities,
  listSnapshots,
} from "./api";
import styles from "./styles/feature-simulation.module.css";
import { useApiResource } from "./use-api-resource";

export interface EligibilityProps {
  readonly unitId: string;
}

const VALIDITY_TONE: Record<ReviewValidity, StatusTone> = {
  CURRENT: "success",
  UNKNOWN: "warning",
  EXPIRED: "warning",
  INVALIDATED: "critical",
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "请求失败，请稍后重试。";
}

export default function EligibilityBlock({ unitId }: EligibilityProps) {
  const loader = useCallback(async () => {
    const [eligibilities, snapshots, baselines, identity] = await Promise.all([
        listEligibilities(unitId),
        listSnapshots(unitId),
        listDecisionBaselines(unitId),
        getCurrentIdentity(),
      ]);
    return {
      eligibilities,
      snapshots,
      baseline: baselines.find((item) => item.state === "FROZEN") ?? null,
      mfaVerified: identity.mfa_verified,
    };
  }, [unitId]);
  const { data, error, refresh } = useApiResource(loader);
  const eligibilities = data?.eligibilities ?? [];
  const snapshots = data?.snapshots ?? [];
  const baseline = data?.baseline ?? null;
  const mfaVerified = data?.mfaVerified ?? false;
  const loaded = data !== null || error !== null;
  const latest = eligibilities[0] ?? null;
  return (
    <PageFrame
      title="推荐资格"
      eyebrow="FR-09a"
      description="基于冻结基线聚合上游有效性；商业审批不属于本资格结论。"
    >
      {error ? <Notice tone="danger" title="无法读取资格数据">{errorMessage(error)}</Notice> : null}
      {!loaded ? <Notice tone="info" title="正在加载">正在读取资格判断与锁定快照。</Notice> : null}
      {loaded && !latest ? (
        <EmptyState title="尚无资格判断" description="请在六项上游有效性均明确后发起评估。" />
      ) : null}
      {latest ? <EligibilitySummary eligibility={latest} /> : null}
      <EligibilityForm
        unitId={unitId}
        baseline={baseline}
        latest={latest}
        disabled={!mfaVerified}
        onChanged={refresh}
      />
      <SnapshotSection
        unitId={unitId}
        eligibility={latest}
        snapshots={snapshots}
        disabled={!mfaVerified}
        onChanged={refresh}
      />
    </PageFrame>
  );
}

function EligibilitySummary({
  eligibility,
}: {
  readonly eligibility: RecommendationEligibility;
}) {
  const reasons = eligibility.blocked_reason_codes ?? [];
  const upstream = Object.entries(eligibility.upstream_validity ?? {});
  const tone: StatusTone =
    eligibility.state === "ELIGIBLE"
      ? "success"
      : eligibility.state === "INELIGIBLE"
        ? "critical"
        : "warning";
  return (
    <>
      <section className={styles.block} aria-label="eligibility-summary">
        <h2 className={styles.blockTitle}>当前判断</h2>
        <div className={styles.blockGrid}>
          <Field label="state"><StatusBadge tone={tone}>{eligibility.state}</StatusBadge></Field>
          <Field label="eligibility_id">{eligibility.eligibility_id}</Field>
          <Field label="version_id">{eligibility.version_id}</Field>
          <Field label="baseline_version_id">{eligibility.baseline_version_id}</Field>
          <Field label="assessed_at">{eligibility.assessed_at}</Field>
          <Field label="snapshot_version_id">{eligibility.snapshot_version_id ?? "—"}</Field>
        </div>
      </section>
      <section className={styles.block} aria-label="upstream-validity">
        <h2 className={styles.blockTitle}>上游有效性</h2>
        {upstream.length === 0 ? (
          <EmptyState title="未返回上游明细" description="资格记录没有附带 upstream_validity。" />
        ) : (
          <div className={styles.blockGrid}>
            {upstream.map(([name, validity]) => (
              <Field key={name} label={name}>
                <StatusBadge tone={VALIDITY_TONE[validity]}>{validity}</StatusBadge>
              </Field>
            ))}
          </div>
        )}
      </section>
      <section className={styles.block} aria-label="blocked-reasons">
        <h2 className={styles.blockTitle}>阻塞原因</h2>
        {reasons.length === 0 ? (
          <p className={styles.caption}>无</p>
        ) : (
          <ul className={styles.reasonList}>
            {reasons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        )}
      </section>
    </>
  );
}

const GATE_NAMES = [
  "precheck",
  "readiness",
  "static_validation",
  "scenario_assessment",
  "condition",
  "risk_acceptance",
] as const;

type GateName = (typeof GATE_NAMES)[number];
type GateValues = Record<GateName, ReviewValidity>;

function EligibilityForm({
  unitId,
  baseline,
  latest,
  disabled,
  onChanged,
}: {
  readonly unitId: string;
  readonly baseline: DecisionBaseline | null;
  readonly latest: RecommendationEligibility | null;
  readonly disabled: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const defaults = Object.fromEntries(
    GATE_NAMES.map((name) => [name, latest?.upstream_validity?.[name] ?? "UNKNOWN"]),
  ) as GateValues;
  const [values, setValues] = useState<GateValues>(defaults);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!baseline) return;
    setPending(true);
    setError(null);
    try {
      await createRecommendationEligibility(unitId, {
        baseline_id: baseline.baseline_id,
        ...values,
      });
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className={styles.block} aria-label="assess-eligibility">
      <h2 className={styles.blockTitle}>发起资格评估</h2>
      <form className={styles.modalPanel} onSubmit={submit}>
        {GATE_NAMES.map((name) => (
          <label key={name}>
            {name}
            <select
              value={values[name]}
              onChange={(event) => setValues({ ...values, [name]: event.target.value as ReviewValidity })}
            >
              <option value="CURRENT">CURRENT</option>
              <option value="UNKNOWN">UNKNOWN</option>
              <option value="EXPIRED">EXPIRED</option>
              <option value="INVALIDATED">INVALIDATED</option>
            </select>
          </label>
        ))}
        {error ? <Notice tone="danger" title="评估失败">{error}</Notice> : null}
        <Button type="submit" disabled={!baseline || disabled || pending}>
          {pending ? "提交中…" : "评估资格"}
        </Button>
        {disabled ? <p className={styles.caption}>此操作需要 MFA 验证。</p> : null}
      </form>
    </section>
  );
}

function SnapshotSection({
  unitId,
  eligibility,
  snapshots,
  disabled,
  onChanged,
}: {
  readonly unitId: string;
  readonly eligibility: RecommendationEligibility | null;
  readonly snapshots: ReadonlyArray<SimulationAssessmentSnapshot>;
  readonly disabled: boolean;
  readonly onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function lockSnapshot() {
    if (!eligibility) return;
    setPending(true);
    setError(null);
    try {
      await createSnapshot(unitId, {
        payload: {
          eligibility_id: eligibility.eligibility_id,
          eligibility_version_id: eligibility.version_id,
          state: eligibility.state,
          blocked_reason_codes: eligibility.blocked_reason_codes ?? [],
          upstream_validity: eligibility.upstream_validity ?? {},
          assessed_at: eligibility.assessed_at,
        },
      });
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  }

  async function download(snapshot: SimulationAssessmentSnapshot) {
    const response = await downloadSnapshot(snapshot.snapshot_id);
    const blob = new Blob([JSON.stringify(response.snapshot, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `simulation-snapshot-${snapshot.snapshot_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className={styles.block} aria-label="assessment-snapshots">
      <h2 className={styles.blockTitle}>锁定快照</h2>
      <Notice tone="warning" title="影子试点材料">
        快照由后端强制添加水印，只用于审计与评估，不能替代商业审批。
      </Notice>
      <div className={`${styles.actions} ${styles.gapMd}`}>
        <Button disabled={!eligibility || disabled || pending} onClick={() => void lockSnapshot()}>
          {pending ? "锁定中…" : "锁定当前资格快照"}
        </Button>
      </div>
      {error ? <Notice tone="danger" title="快照失败">{error}</Notice> : null}
      {snapshots.length === 0 ? (
        <EmptyState title="尚无快照" description="完成资格判断后可锁定审计快照。" />
      ) : (
        <table className={`${styles.table} ${styles.gapMd}`}>
          <thead><tr><th>snapshot_id</th><th>state</th><th>watermark</th><th>created_at</th><th>下载</th></tr></thead>
          <tbody>
            {snapshots.map((snapshot) => (
              <tr key={snapshot.snapshot_id} className={styles.tableRow}>
                <td>{snapshot.snapshot_id}</td><td>{snapshot.state}</td><td>{snapshot.watermark}</td><td>{snapshot.created_at}</td>
                <td><Button variant="quiet" onClick={() => void download(snapshot)}>JSON</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
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
