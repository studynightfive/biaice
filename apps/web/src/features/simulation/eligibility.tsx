/**
 * /eligibility page block.
 *
 * Composition:
 *   1. State banner (ELIGIBLE / ELIGIBLE_WITH_ACCEPTED_RISK /
 *      ELIGIBLE_WITH_CONDITIONS / NOT_ELIGIBLE / INDETERMINATE).
 *   2. Input aggregate (precheck / readiness / static / scenario /
 *      condition / risk-acceptance validity state).
 *   3. Blocking reasons + open conditions (commercial approval excluded).
 *   4. SimulationAssessmentSnapshot panel (always watermarked; download
 *      payload action returns the verbatim backend payload).
 */

import { EmptyState, Notice, StatusBadge, type StatusTone } from "@/components/ui";
import { PageFrame } from "@/components/shell/page-frame";

import styles from "./styles/feature-simulation.module.css";

import { listEligibilities, listSnapshots } from "./api";
import { EligibilityStateBanner } from "./components/eligibility-state-banner";
import { SnapshotWatermark } from "./components/snapshot-watermark";
import type { RecommendationEligibilityVersion, SimulationAssessmentSnapshot, ValidityState } from "./types";

export interface EligibilityProps {
  unitId: string;
  mfaVerified: boolean;
}

const VALIDITY_TONE: Record<ValidityState, StatusTone> = {
  CURRENT: "success",
  STALE: "warning",
  EXPIRED: "warning",
  INVALIDATED: "critical",
  UNKNOWN: "neutral",
};

export default async function EligibilityBlock({ unitId, mfaVerified }: EligibilityProps) {
  const eligibilities = await listEligibilities(unitId);
  const snapshots = await listSnapshots(unitId);
  const latest = eligibilities[0] ?? null;
  const latestSnapshot = snapshots[0] ?? null;

  return (
    <PageFrame
      title="Recommendation eligibility"
      eyebrow="member 6" description="Aggregates the current upstream gates; does not include any commercial approval."
    >
      {!latest ? (
        <Notice tone="warning" title="No eligibility verdict">
          A RecommendationEligibilityVersion has not been produced for this unit. The page never infers
          eligibility from other sources.
        </Notice>
      ) : (
        <EligibilityStateBanner
          state={latest.state}
          blockingReasonCount={latest.blocking_reasons.length}
          conditionalCount={latest.eligible_with_conditions.length}
          evaluatedAt={latest.evaluated_at}
          excludesCommercialApproval={!latest.includes_commercial_approval}
        />
      )}
      {latest ? <InputsAggregate latest={latest} /> : null}
      {latest ? (
        <BlockingReasonsSection
          latest={latest}
          canReassess={mfaVerified && latest.state !== "INDETERMINATE"}
        />
      ) : null}
      <SnapshotSection snapshot={latestSnapshot} />
    </PageFrame>
  );
}

function InputsAggregate({ latest }: { latest: RecommendationEligibilityVersion }) {
  const entries: Array<[string, ValidityState]> = [
    ["precheck_state", latest.inputs.precheck_state],
    ["readiness_state", latest.inputs.readiness_state],
    ["static_validation_state", latest.inputs.static_validation_state],
    ["scenario_assessment_state", latest.inputs.scenario_assessment_state],
    ["condition_state", latest.inputs.condition_state],
    ["risk_acceptance_state", latest.inputs.risk_acceptance_state],
  ];
  return (
    <section className={styles.block} aria-label="input-aggregate">
      <h2 className={styles.blockTitle}>
        Input aggregate <small>{latest.evaluator_version}</small>
      </h2>
      <div className={styles.blockGrid}>
        {entries.map(([label, value]) => (
          <div key={label} className={styles.field}>
            <span className={styles.fieldLabel}>{label}</span>
            <span className={styles.fieldValue}>
              <StatusBadge tone={VALIDITY_TONE[value]}>{value}</StatusBadge>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function BlockingReasonsSection({ latest, canReassess }: { latest: RecommendationEligibilityVersion; canReassess: boolean }) {
  return (
    <section className={styles.block} aria-label="blocking-reasons">
      <h2 className={styles.blockTitle}>Blocking reasons &amp; open conditions</h2>
      <div className={styles.blockGrid}>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Blocking reasons ({latest.blocking_reasons.length})</span>
          {latest.blocking_reasons.length === 0 ? (
            <span className={styles.fieldValue}>None.</span>
          ) : (
            <ul className={styles.reasonList}>
              {latest.blocking_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </div>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Open conditions ({latest.eligible_with_conditions.length})</span>
          {latest.eligible_with_conditions.length === 0 ? (
            <span className={styles.fieldValue}>None.</span>
          ) : (
            <ul className={styles.reasonList}>
              {latest.eligible_with_conditions.map((c) => (
                <li key={c.condition_id} data-tone="warn">
                  blocks <strong>{c.blocked_stage}</strong> · {c.description}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <p className={styles.caption + " " + styles.gapSm}>
        Commercial approval is not part of this verdict.
        {canReassess ? " Reassessment requires a verified session and the snapshot block above to be closed." : null}
      </p>
    </section>
  );
}

function SnapshotSection({ snapshot }: { snapshot: SimulationAssessmentSnapshot | null }) {
  if (!snapshot) {
    return (
      <section className={styles.block} aria-label="snapshot">
        <h2 className={styles.blockTitle}>Simulation assessment snapshot</h2>
        <EmptyState
          title="No snapshot created yet"
          description="Once an eligibility verdict exists, the MVP-B pipeline may create a SHADOW snapshot for downstream consumers."
        />
      </section>
    );
  }
  return (
    <section className={styles.block} aria-label="snapshot">
      <h2 className={styles.blockTitle}>
        Simulation assessment snapshot <small>{snapshot.version}</small>
      </h2>
      <SnapshotWatermark caption={"该快照不能被审批、不能被作为提交授权、仅供下游受控消费。"}>
        <div className={styles.blockGrid + " " + styles.gapMd}>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>snapshot_id</span>
            <span className={styles.fieldValue}>{snapshot.id}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>eligibility_version_id</span>
            <span className={styles.fieldValue}>{snapshot.eligibility_version_id}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>batch_id</span>
            <span className={styles.fieldValue}>{snapshot.batch_id ?? "—"}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>run_id</span>
            <span className={styles.fieldValue}>{snapshot.run_id ?? "—"}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>created_at</span>
            <span className={styles.fieldValue}>{snapshot.created_at}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>watermark</span>
            <span className={styles.fieldValue}>{snapshot.watermark}</span>
          </div>
        </div>
        <p className={styles.caption + " " + styles.gapSm}>
          The payload URL below always serves the verbatim backend payload; the page never re-derives probabilities or recomputes coverage.
        </p>
        <SnapshotDownloadIsland snapshotId={snapshot.id} payloadUrl={snapshot.payload_url} />
      </SnapshotWatermark>
    </section>
  );
}

async function SnapshotDownloadIsland({ snapshotId, payloadUrl }: { snapshotId: string; payloadUrl: string }) {
  const mod = await import("./eligibility.client");
  return <mod.SnapshotDownloadClient snapshotId={snapshotId} payloadUrl={payloadUrl} />;
}
