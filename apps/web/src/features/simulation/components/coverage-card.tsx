"use client";

import { Card } from "@/components/ui";

import styles from "../styles/feature-simulation.module.css";

import type { CoverageInterval } from "../types";
import { formatPercent } from "../format";

export interface CoverageCardProps {
  coverage: CoverageInterval | null;
  runId?: string;
  basis?: string;
}

export function CoverageCard({ coverage, runId, basis }: CoverageCardProps) {
  if (!coverage) {
    return (
      <Card title="Coverage & N_eff">
        <p className={styles.fieldValue} role="status" aria-live="polite">
          分母低于协议阈值，结果 UNDEFINED。
        </p>
        <p className={styles.caption + " " + styles.gapSm}>
          Coverage / N_eff are only available once the run publishes a structured coverage record.
        </p>
      </Card>
    );
  }

  const altText = describeCoverage(coverage, runId, basis);

  return (
    <Card title="Coverage & N_eff">
      <div className={styles.coverageCard}>
        <div className={styles.coverageFigure}>
          <span className={styles.figureLabel}>[P−, P⁺]</span>
          <span className={styles.figureValue}>
            {formatPercent(coverage.lower, coverage.upper, { lower: coverage.lower_mc_ci, upper: coverage.upper_mc_ci })}
          </span>
        </div>
        <div className={styles.coverageFigure}>
          <span className={styles.figureLabel}>Coverage</span>
          <span className={styles.figureValue}>
            {coverage.coverage === "UNDEFINED" ? "UNDEFINED" : coverage.coverage}
          </span>
        </div>
        <div className={styles.coverageFigure}>
          <span className={styles.figureLabel}>N_eff</span>
          <span className={styles.figureValue}>
            {coverage.n_eff === "UNDEFINED" ? "UNDEFINED" : coverage.n_eff}
          </span>
        </div>
        <div className={styles.coverageFigure}>
          <span className={styles.figureLabel}>Denominator</span>
          <span className={styles.figureValue}>
            {coverage.denominator === "UNDEFINED" ? "UNDEFINED" : coverage.denominator}
          </span>
        </div>
      </div>
      <p aria-label={altText} className={styles.coverageAlt + " " + styles.gapMd}>
        {coverage.basis}
      </p>
      <p className={styles.coverageHint + " " + styles.gapSm}>
        此为部分识别区间，不是单点概率。
      </p>
    </Card>
  );
}

function describeCoverage(coverage: CoverageInterval, runId?: string, basis?: string): string {
  const lower = String(coverage.lower);
  const upper = String(coverage.upper);
  const cov = coverage.coverage === "UNDEFINED" ? "undefined" : String(coverage.coverage);
  const nEff = coverage.n_eff === "UNDEFINED" ? "undefined" : String(coverage.n_eff);
  const runSuffix = runId ? " run " + runId : "";
  const basisSuffix = basis ? " basis " + basis : "";
  return "Partial identification interval [" + lower + ", " + upper + "], coverage " + cov + ", N_eff " + nEff + runSuffix + basisSuffix + ".";
}

export default CoverageCard;
