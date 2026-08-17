"use client";

import styles from "../styles/feature-simulation.module.css";

import type { StressAxisKind, StressTestAssessment } from "../types";

export interface StressAxisChipProps {
  axis: StressTestAssessment;
  currency?: string;
}

const AXIS_LABELS: Record<StressAxisKind, string> = {
  COST_INFLATION: "Cost inflation",
  COMPETITOR_PRICE_CUT: "Competitor price cut",
  RESPONSE_QUALITY_BOOST: "Response quality boost",
  UNKNOWN_ENTRANT: "Unknown entrant",
  EVIDENCE_WITHDRAWN: "Evidence withdrawn",
  RULE_BOUNDARY: "Rule boundary jump",
};

const AXIS_ICONS: Record<StressAxisKind, string> = {
  COST_INFLATION: "↑",
  COMPETITOR_PRICE_CUT: "↓",
  RESPONSE_QUALITY_BOOST: "✱",
  UNKNOWN_ENTRANT: "?",
  EVIDENCE_WITHDRAWN: "✕",
  RULE_BOUNDARY: "⚠",
};

export function StressAxisChip({ axis, currency }: StressAxisChipProps) {
  const label = AXIS_LABELS[axis.axis] ?? axis.axis;
  const icon = AXIS_ICONS[axis.axis] ?? "·";
  const worstValue = axis.worst_value
    ? currency
      ? currency + " " + axis.worst_value.value
      : axis.worst_value.value
    : null;
  return (
    <div className={styles.stressChip} data-outcome={axis.outcome} role="group" aria-label={"stress-" + axis.axis}>
      <div className={styles.stressChipHeader}>
        <span>
          <span aria-hidden="true" className={styles.stressIcon}>{icon}</span>
          {label}
        </span>
        <span className={styles.status + " " + (axis.outcome === "PASS" ? styles.statusIsOk : axis.outcome === "FAIL" ? styles.statusIsFail : styles.statusIsWarn)}>
          {axis.outcome}
        </span>
      </div>
      <div className={styles.stressChipValue}>
        Affected: {axis.affected_candidate_count} candidate(s)
        {worstValue ? <span> · worst value {worstValue}</span> : null}
      </div>
      {axis.notes ? <div className={styles.stressChipValue}>{axis.notes}</div> : null}
    </div>
  );
}

export function StressAxisGrid({ axes, currency }: { axes: StressTestAssessment[]; currency?: string }) {
  const allAxes: StressAxisKind[] = [
    "COST_INFLATION",
    "COMPETITOR_PRICE_CUT",
    "RESPONSE_QUALITY_BOOST",
    "UNKNOWN_ENTRANT",
    "EVIDENCE_WITHDRAWN",
    "RULE_BOUNDARY",
  ];
  const byKind: Partial<Record<StressAxisKind, StressTestAssessment>> = {};
  for (let i = 0; i < axes.length; i += 1) {
    const axis = axes[i];
    byKind[axis.axis] = axis;
  }
  return (
    <div className={styles.stressGrid}>
      {allAxes.map((kind) => {
        const assessment = byKind[kind] ?? { axis: kind, outcome: "INDETERMINATE" as const, affected_candidate_count: 0 };
        return <StressAxisChip key={kind} axis={assessment} currency={currency} />;
      })}
    </div>
  );
}

export default StressAxisChip;
