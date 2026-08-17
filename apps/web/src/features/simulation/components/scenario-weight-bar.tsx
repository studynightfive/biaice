"use client";

import styles from "../styles/feature-simulation.module.css";

import type { ScenarioSpec } from "../types";

export interface ScenarioWeightBarProps {
  probability: ReadonlyArray<ScenarioSpec>;
  stress: ReadonlyArray<ScenarioSpec>;
  totalProbabilityWeight: string;
}

export function ScenarioWeightBar({ probability, stress, totalProbabilityWeight }: ScenarioWeightBarProps) {
  const probTotal = sumWeights(probability);
  const stressTotal = sumWeights(stress);
  const combined = probTotal + stressTotal;
  const probRatio = combined === 0 ? 0 : (probTotal / combined) * 100;
  const stressRatio = combined === 0 ? 0 : (stressTotal / combined) * 100;

  return (
    <div aria-label="scenario-weight-distribution" role="group">
      <div className={styles.weightBar} aria-hidden="true">
        <div className={styles.weightBarProb} style={{ width: probRatio + "%" }} />
        <div className={styles.weightBarStress} style={{ width: stressRatio + "%" }} />
      </div>
      <div className={styles.weightBarLegend}>
        <span className="swatchProb">PROBABILITY · {probTotal.toFixed(4)} (declared {totalProbabilityWeight})</span>
        <span className="swatchStress" title="STRESS weights never enter the probability denominator.">
          STRESS · {stressTotal.toFixed(4)} (not in probability denominator)
        </span>
      </div>
      <p className={styles.weightNote}>
        {probability.length} PROBABILITY scenario(s) + {stress.length} STRESS scenario(s). 
        STRESS scenarios never enter the probability denominator and only feed the mandatory stress axis set.
      </p>
    </div>
  );
}

function sumWeights(scenarios: ReadonlyArray<ScenarioSpec>): number {
  let total = 0;
  for (let i = 0; i < scenarios.length; i += 1) {
    const raw = scenarios[i].weight;
    const value = Number(raw);
    if (Number.isFinite(value)) total += value;
  }
  return total;
}

export default ScenarioWeightBar;
