"use client";

import { StatusBadge, type StatusTone } from "@/components/ui";

import styles from "../styles/feature-simulation.module.css";

import type { EligibilityState } from "../types";

export interface EligibilityStateBannerProps {
  state: EligibilityState | "NONE";
  blockingReasonCount: number;
  conditionalCount: number;
  evaluatedAt?: string;
  excludesCommercialApproval?: boolean;
}

const STATE_TONE: Record<EligibilityState, StatusTone> = {
  ELIGIBLE: "success",
  ELIGIBLE_WITH_ACCEPTED_RISK: "info",
  ELIGIBLE_WITH_CONDITIONS: "warning",
  INELIGIBLE: "critical",
  INDETERMINATE: "neutral",
  NOT_ELIGIBLE: "critical",
};

const STATE_COPY: Record<EligibilityState | "NONE", { title: string; description: string }> = {
  ELIGIBLE: {
    title: "ELIGIBLE",
    description: "All required gates are CURRENT. This is the recommendation-eligibility verdict only; it does not authorise submission.",
  },
  ELIGIBLE_WITH_ACCEPTED_RISK: {
    title: "ELIGIBLE · WITH ACCEPTED RISK",
    description: "All gates passed, but the current RiskAcceptanceVersion is required to keep the verdict open. Withdraw the acceptance and the verdict reverts.",
  },
  ELIGIBLE_WITH_CONDITIONS: {
    title: "ELIGIBLE · WITH CONDITIONS",
    description: "Open conditions remain — each is mapped to the exact stage it blocks. No commercial approval is included in this verdict.",
  },
  INELIGIBLE: {
    title: "INELIGIBLE",
    description: "One or more required gates are blocked. Open the blocking-reasons panel to see which stage is failing.",
  },
  NOT_ELIGIBLE: {
    title: "NOT ELIGIBLE",
    description: "At least one upstream gate is blocked or invalid.",
  },
  INDETERMINATE: {
    title: "INDETERMINATE",
    description: "Inputs are still UNKNOWN / EXPIRED / INVALIDATED. The verdict cannot be computed.",
  },
  NONE: {
    title: "No eligibility verdict yet",
    description: "A RecommendationEligibilityVersion has not been produced for this unit yet.",
  },
};

export function EligibilityStateBanner({
  state,
  blockingReasonCount,
  conditionalCount,
  evaluatedAt,
  excludesCommercialApproval = true,
}: EligibilityStateBannerProps) {
  var copy = STATE_COPY[state] ?? STATE_COPY.INDETERMINATE;
  var tone: StatusTone = state === "NONE" ? "neutral" : STATE_TONE[state] ?? "neutral";
  return (
    <section className={styles.eligibilityBanner} data-state={state} aria-label="eligibility-state">
      <StatusBadge tone={tone} label={copy.title} />
      <div className={styles.eligibilityBannerBody}>
        <strong>{copy.title}</strong>
        <p>{copy.description}</p>
        <p className={styles.caption}>
          Blocking reasons: {blockingReasonCount} · Open conditions: {conditionalCount}
          {evaluatedAt ? " · Evaluated at " + evaluatedAt : null}
        </p>
        <p className={styles.caption}>
          {excludesCommercialApproval
            ? "This verdict excludes any commercial approval.",
            : "Commercial approval was included — out of scope for FR-09a."}
        </p>
      </div>
    </section>
  );
}

export default EligibilityStateBanner;
