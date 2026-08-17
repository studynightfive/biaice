/**
 * /baseline-scenarios page block.
 *
 * The block is composed of three sections:
 *   1. Frozen baseline   — the DecisionBaselineVersion (and any superseded
 *      siblings) together with input_manifest_hash, as-of and the list of
 *      frozen references.
 *   2. Candidate search space — the latest CandidateSearchSpaceVersion and
 *      an action to request a new one (MFA is required; the button is
 *      disabled until the current baseline is COMPLETE + CURRENT).
 *   3. Scenario set      — PROBABILITY scenarios, STRESS scenarios and the
 *      ScenarioSetVersion state.
 *
 * The block is a server component (no "use client") because every fetch
 * goes through the server-only getBiaiceClient() wrapper and the page
 * must always reflect the latest backend state.
 */

import { Card, EmptyState, Notice, type StatusTone } from "@/components/ui";
// Member 1 owns the page frame component; we consume it through the shared alias.
import { PageFrame } from "@/components/shell/page-frame";

import styles from "./styles/feature-simulation.module.css";

import { loadBaselineBundle } from "./api";
import { ScenarioWeightBar } from "./components/scenario-weight-bar";
import { CopyHashButton } from "./components/copy-hash-button";
import { formatHash, formatMoney } from "./format";
import {
  deriveBaselineReadiness,
  type BaselineBundle,
  type CandidateSearchSpaceVersion,
  type DecisionBaselineVersion,
  type Readiness,
  type ScenarioSetVersion,
  type ValidityState,
} from "./types";

export interface BaselineScenariosProps {
  unitId: string;
  /**
   * true when the active session is multi-factor authenticated. The page
   * uses this to gate the create-search-space action (member 7's RiskAcceptance
   * port and member 1's MFA guard are both required for freeze actions).
   */
  mfaVerified: boolean;
}

const READINESS_TONE: Record<Readiness, StatusTone> = {
  READY: "success",
  STALE: "warning",
  INCOMPLETE: "warning",
  INDETERMINATE: "neutral",
  FAIL: "critical",
  NOT_PRESENT: "neutral",
};

const READINESS_LABEL: Record<Readiness, string> = {
  READY: "Ready",
  STALE: "Stale",
  INCOMPLETE: "Incomplete",
  INDETERMINATE: "Indeterminate",
  FAIL: "Failed",
  NOT_PRESENT: "Not present",
};

const VALIDITY_TONE: Record<ValidityState, StatusTone> = {
  CURRENT: "success",
  STALE: "warning",
  EXPIRED: "warning",
  INVALIDATED: "critical",
  UNKNOWN: "neutral",
};

export default async function BaselineScenariosBlock({ unitId, mfaVerified }: BaselineScenariosProps) {
  var bundle = await loadBaselineBundle(unitId);
  var readiness = deriveBaselineReadiness(bundle.current, bundle.superseded);
  return (
    <PageFrame title="Decision baseline & scenario set" eyebrow="member 6" description="Freeze the search/evaluation scenario set so the simulation batch can run on stable inputs.">
      <ReadinessBar readiness={readiness} bundle={bundle} />
      {!bundle.current ? (
        <Notice tone="danger" title="No frozen baseline">
          The unit has not produced a DecisionBaselineVersion yet. Without a frozen baseline the simulation feature cannot create batches. Open the upstream readiness workstream first.
        </Notice>
      ) : null}
      {bundle.current && !bundle.current.is_complete ? (
        <Notice tone="danger" title="Baseline is incomplete">
          The current baseline lists at least one missing frozen input. Simulation batches are blocked until the baseline reaches <strong>is_complete = true</strong>.
        </Notice>
      ) : null}
      <BaselineSection current={bundle.current} superseded={bundle.superseded} />
      <SearchSpaceSection unitId={unitId} spaces={bundle.searchSpaces} canRequest={mfaVerified && readiness.status === "READY"} />
      <ScenarioSetSection sets={bundle.scenarioSets} canFreeze={readiness.status === "READY"} />
    </PageFrame>
  );
}

function ReadinessBar({ readiness, bundle }: { readiness: { status: Readiness; reason_codes: string[] }; bundle: BaselineBundle }) {
  var readinessTone = READINESS_TONE[readiness.status];
  var readinessClass =
    readinessTone === "success" ? styles.statusIsOk
      : readinessTone === "warning" ? styles.statusIsWarn
        : readinessTone === "critical" ? styles.statusIsFail
          : styles.statusIsInfo;
  return (
    <div className={styles.readinessBar} role="status" aria-live="polite">
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Baseline</span>
          <span className={styles.fieldValue + " " + readinessClass}>{READINESS_LABEL[readiness.status]}</span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Search spaces</span>
          <span className={styles.fieldValue}>{bundle.searchSpaces.length} version(s)</span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Scenario sets</span>
          <span className={styles.fieldValue}>{bundle.scenarioSets.length} version(s)</span>
        </div>
      </Card>
      <Card>
        <div className={styles.field}>
          <span className={styles.fieldLabel}>Reason codes</span>
          <span className={styles.fieldValue}>{readiness.reason_codes.length === 0 ? "—" : readiness.reason_codes.join(", ")}</span>
        </div>
      </Card>
    </div>
  );
}

function BaselineSection({ current, superseded }: { current: DecisionBaselineVersion | null; superseded: DecisionBaselineVersion[] }) {
  if (!current && superseded.length === 0) {
    return (
      <section className={styles.block} aria-label="frozen-baseline">
        <h2 className={styles.blockTitle}>Frozen baseline</h2>
        <EmptyState title="No baseline version" description="Create the first DecisionBaselineVersion to begin." />
      </section>
    );
  }
  return (
    <section className={styles.block} aria-label="frozen-baseline">
      <h2 className={styles.blockTitle}>
        Frozen baseline <small>{current ? current.version : "superseded"}</small>
      </h2>
      {current ? <BaselineDetails baseline={current} /> : null}
      {superseded.length > 0 ? (
        <div className={styles.gapLg}>
          <h3 className={styles.blockTitle + " " + styles.caption} id="superseded-baselines">Superseded baselines</h3>
          <table className={styles.table} aria-labelledby="superseded-baselines">
            <thead>
              <tr>
                <th scope="col">Version</th>
                <th scope="col">Validity</th>
                <th scope="col">Created at</th>
                <th scope="col">Hash</th>
              </tr>
            </thead>
            <tbody>
              {superseded.map((b) => {
                var tone = VALIDITY_TONE[b.validity_state];
                var cls =
                  tone === "success" ? styles.statusIsOk
                    : tone === "warning" ? styles.statusIsWarn
                      : tone === "critical" ? styles.statusIsFail
                        : styles.statusIsInfo;
                return (
                  <tr key={b.id} className={styles.tableRow}>
                    <td>{b.version}</td>
                    <td>
                      <span className={styles.status + " " + cls}>{b.validity_state}</span>
                    </td>
                    <td>{b.created_at}</td>
                    <td><span className={styles.hashMono}>{formatHash(b.input_manifest_hash)}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className={styles.caption + " " + styles.gapSm}>已过时，仅展示。</p>
        </div>
      ) : null}
    </section>
  );
}

function BaselineDetails({ baseline }: { baseline: DecisionBaselineVersion }) {
  return (
    <div className={styles.blockGrid}>
      <Field label="Rule set">{baseline.frozen_rule_set_version}</Field>
      <Field label="Response profile">{baseline.frozen_response_profile_version}</Field>
      <Field label="Cost baseline">{baseline.frozen_cost_baseline_version}</Field>
      <Field label="Commercial policy">{baseline.frozen_commercial_policy_version}</Field>
      <Field label="Model artifact">{baseline.frozen_model_artifact_version}</Field>
      <Field label="as_of">{baseline.as_of}</Field>
      <Field label="Competitor profiles">{baseline.frozen_competitor_profiles.length === 0 ? "none" : baseline.frozen_competitor_profiles.join(", ")}</Field>
      <Field label="Market priors">{baseline.frozen_market_priors.length === 0 ? "none" : baseline.frozen_market_priors.join(", ")}</Field>
      <Field label="Unknown entrant profile">{baseline.frozen_unknown_entrant_profile ?? "none"}</Field>
      <Field label="is_complete">{baseline.is_complete ? "yes" : "no"}</Field>
      <Field label="Validity">{baseline.validity_state}</Field>
      <Field label="Input manifest hash">
        <span className={styles.hashMono}>
          {formatHash(baseline.input_manifest_hash)}
          <CopyHashButton value={baseline.input_manifest_hash} label="copy-baseline-hash" />
        </span>
      </Field>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <span className={styles.fieldValue}>{children}</span>
    </div>
  );
}

function SearchSpaceSection({ unitId, spaces, canRequest }: { unitId: string; spaces: CandidateSearchSpaceVersion[]; canRequest: boolean }) {
  var latest = spaces[0] ?? null;
  return (
    <section className={styles.block} aria-label="candidate-search-space">
      <h2 className={styles.blockTitle}>
        Candidate search space <small>{latest ? latest.version : "none"}</small>
      </h2>
      {latest ? (
        <div className={styles.blockGrid}>
          <Field label="Lower bound">{formatMoney(latest.lower_bound, latest.currency)}</Field>
          <Field label="Upper bound">{formatMoney(latest.upper_bound, latest.currency)}</Field>
          <Field label="Step">{latest.step}</Field>
          <Field label="Precision">{latest.precision}</Field>
          <Field label="Rounding">{latest.rounding_mode}</Field>
          <Field label="Tax passthrough">{latest.tax_passthrough ? "yes" : "no"}</Field>
          <Field label="Abnormal low jump points">
            {latest.abnormal_low_jump_points.length === 0 ? "—" : latest.abnormal_low_jump_points.join(", ")}
          </Field>
          <Field label="Commercial exploration bounds">
            {formatMoney(latest.commercial_exploration_bounds.lower, latest.currency)} → {formatMoney(latest.commercial_exploration_bounds.upper, latest.currency)}
          </Field>
          <Field label="Baseline">{latest.baseline_version_id}</Field>
          <Field label="Validity">{latest.validity_state}</Field>
        </div>
      ) : (
        <EmptyState title="No search space yet" description="Request the first CandidateSearchSpaceVersion once the baseline is ready." />
      )}
      <div className={styles.actions}>
        <RequestSearchSpaceButton unitId={unitId} disabled={!canRequest} />
      </div>
      {!canRequest ? (
        <p className={styles.caption + " " + styles.gapSm}>
          {!latest && spaces.length === 0
            ? "需要先有一个已完成、当前生效的决策基线。" 
            : "请确保决策基线状态为 READY、会话 MFA 已验证。"}
        </p>
      ) : null}
    </section>
  );
}

function ScenarioSetSection({ sets, canFreeze }: { sets: ScenarioSetVersion[]; canFreeze: boolean }) {
  var latest = sets[0] ?? null;
  return (
    <section className={styles.block} aria-label="scenario-set">
      <h2 className={styles.blockTitle}>
        Scenario set <small>{latest ? latest.version : "none"}</small>
      </h2>
      {latest ? (
        <div className={styles.blockGrid + " " + styles.gapMd}>
          <Field label="Search seed">{latest.random_seed}</Field>
          <Field label="Search set">{latest.search_set_id ?? "—"}</Field>
          <Field label="Evaluation set">{latest.evaluation_set_id ?? "—"}</Field>
          <Field label="Total probability weight">{String(latest.total_probability_weight)}</Field>
          <Field label="Baseline">{latest.baseline_version_id}</Field>
          <Field label="Validity">{latest.validity_state}</Field>
        </div>
      ) : null}
      {latest ? (
        <div className={styles.gapLg}>
          <ScenarioWeightBar
            probability={latest.probability_scenarios}
            stress={latest.stress_scenarios}
            totalProbabilityWeight={String(latest.total_probability_weight)}
          />
          <h3 className={styles.blockTitle + " " + styles.caption} id="probability-scenarios">Probability scenarios (in denominator)</h3>
          <ScenarioTable scenarios={latest.probability_scenarios} />
          <h3 className={styles.blockTitle + " " + styles.caption + " " + styles.gapMd} id="stress-scenarios">Stress scenarios (not in probability denominator)</h3>
          <ScenarioTable scenarios={latest.stress_scenarios} />
          <p className={styles.caption + " " + styles.gapSm}>
            STRESS 权重从不进入概率分母，仅进入强制压力轴集。
          </p>
        </div>
      ) : (
        <EmptyState title="No scenario set yet" description="Freeze the first ScenarioSetVersion once the baseline is ready." />
      )}
    </section>
  );
}

function ScenarioTable({ scenarios }: { scenarios: ScenarioSetVersion["probability_scenarios"] }) {
  if (scenarios.length === 0) {
    return <EmptyState title="No scenarios of this kind" description="The frozen scenario set contains no entries of this kind." />;
  }
  return (
    <table className={styles.table} aria-label="scenario-table">
      <thead>
        <tr>
          <th scope="col">scenario_id</th>
          <th scope="col">weight</th>
          <th scope="col">generator_parameters</th>
        </tr>
      </thead>
      <tbody>
        {scenarios.map((spec) => (
          <tr key={spec.scenario_id} className={styles.tableRow}>
            <td>{spec.scenario_id}</td>
            <td>{String(spec.weight)}</td>
            <td><code>{JSON.stringify(spec.generator_parameters)}</code></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Freeze action is implemented in a small client island; see baseline-scenarios.client.tsx
async function RequestSearchSpaceButton({ unitId, disabled }: { unitId: string; disabled: boolean }) {
  var mod = await import("./baseline-scenarios.client");
  return <mod.RequestSearchSpaceButtonClient unitId={unitId} disabled={disabled} />;
}
