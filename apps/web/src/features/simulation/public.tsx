/**
 * Public entry surface for the simulation feature.
 *
 * Member 1 (the integration owner) is the only consumer of this file.
 * Every other team member's code must reach the feature through one of
 * the three *Mount components exported below.
 *
 * The mounts are thin entry points. Data is loaded in the browser through
 * the same-origin BFF so HttpOnly OIDC cookies remain protected.
 */

import BaselineScenariosBlock from "./baseline-scenarios";
import EligibilityBlock from "./eligibility";
import SimulationBlock from "./simulation";

/**
 * Dynamic route parameters are required; silently substituting an empty unit
 * identifier would turn every request into an invalid API call.
 */
export interface MountProps {
  readonly unitId: string;
}

export function BaselineScenariosMount({ unitId }: MountProps) {
  return <BaselineScenariosBlock unitId={unitId} />;
}

export function SimulationMount({ unitId }: MountProps) {
  return <SimulationBlock unitId={unitId} />;
}

export function EligibilityMount({ unitId }: MountProps) {
  return <EligibilityBlock unitId={unitId} />;
}

