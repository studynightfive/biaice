"use client";

import { Card } from "@/components/ui";

import styles from "../styles/feature-simulation.module.css";

import type { ObjectiveKind, StrategyPlanVersion } from "../types";

export interface PlanObjectiveCardProps {
  plan: StrategyPlanVersion;
  /** Run id this plan belongs to (used for accessibility text). */
  runId: string;
  /** Currency code expected for any money in this plan. */
  currency?: string;
}

const OBJECTIVE_TITLES: Record<ObjectiveKind, string> = {
  RANK_LOWER_BOUND: "Ranking lower-bound priority",
  PROXY_VALUE: "First-candidate economic proxy",
  EXPECTED_VALUE: "Expected decision value",
  CVAR_TAIL: "Tail-loss protection (CVaR)",
  BALANCED: "Balanced composite",
};

const OBJECTIVE_RISK_HINTS: Record<ObjectiveKind, string> = {
  RANK_LOWER_BOUND: "Optimises for the conservative ranking bound; may sacrifice economic value.",
  PROXY_VALUE: "Proxy mode until the award-decision model is approved by member 5.",
  EXPECTED_VALUE: "Requires the approved award-decision model (not yet published in MVP-B).",
  CVAR_TAIL: "Requires an approved CVaR model — until then this card is shown as a watermarked exploration only.",
  BALANCED: "Composite of Z(P), Z(value), Z(margin), Z(review-risk) and Z(CVaR).",
};

/**
 * Renders a single StrategyPlanVersion as a card. The card is plain when
 * the plan is in PROXY mode (the award-decision model is not yet approved)
 * and dashed-bordered when the underlying objective is CVAR_TAIL because
 * PRD V1.3 explicitly forbids approving CVaR-based plans before the proxy
 * has been promoted.
 */
export function PlanObjectiveCard({ plan, runId, currency }: PlanObjectiveCardProps) {
  const isProxy = plan.proxy_mode;
  const isCvar = plan.objective === "CVAR_TAIL";
  const cardClass = styles.planCard + (isProxy || isCvar ? " " + styles.planCardProxy : "");
  const title = OBJECTIVE_TITLES[plan.objective] ?? plan.objective;
  const risk = OBJECTIVE_RISK_HINTS[plan.objective] ?? "Objective kind " + plan.objective + ".";

  return (
    <div
      className={cardClass}
      role="group"
      aria-label={"plan-" + plan.objective + "-" + plan.id + "-run-" + runId}
    >
      <div className={styles.planCardTitle}>
        <span>{title}</span>
        <span className={styles.status + " " + (plan.state === "PUBLISHED" ? styles.statusIsOk : styles.statusIsInfo)}>
          {plan.state}
        </span>
      </div>
      <div className={styles.planCardValue}>
        Feasible candidates: {plan.feasible_count}
      </div>
      <div className={styles.planCardMeta}>
        {plan.candidate_ids.length} candidate(s) evaluated, blockers: 
        {plan.blocker_codes.length === 0 ? "none" : plan.blocker_codes.join(", ")}.
      </div>
      <div className={styles.planCardMeta}>{risk}</div>
      {isProxy ? (
        <div className={styles.status + " " + styles.statusIsWarn} role="status">
          Watermarked exploration — proxy mode (no approved award-decision model).
        </div>
      ) : null}
      {isCvar ? (
        <div className={styles.status + " " + styles.statusIsWarn} role="status">
          CVaR plan displayed as watermarked exploration only.
        </div>
      ) : null}
      {plan.rationale ? (
        <div className={styles.planCardMeta}>
          Rationale: {plan.rationale}
        </div>
      ) : null}
      {currency ? (
        <div className={styles.planCardMeta}>Currency: {currency}</div>
      ) : null}
    </div>
  );
}

/**
 * Renders a 0–4 card grid for a set of StrategyPlanVersions. When the set is
 * empty the caller is expected to render EmptyState instead; this helper is
 * for the populated case only.
 */
export function PlanObjectiveGrid({ plans, runId, currency }: { plans: StrategyPlanVersion[]; runId: string; currency?: string }) {
  if (plans.length === 0) {
    return null;
  }
  return (
    <div className={styles.planGrid}>
      {plans.map((plan) => (
        <PlanObjectiveCard key={plan.id} plan={plan} runId={runId} currency={currency} />
      ))}
    </div>
  );
}

export default PlanObjectiveCard;
