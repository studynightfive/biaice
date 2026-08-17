/**
 * Public entry surface for the simulation feature.
 *
 * Member 1 (the integration owner) is the only consumer of this file.
 * Every other team member's code must reach the feature through one of
 * the three *Mount components exported below.
 *
 * The mounts are thin async server components that load the latest
 * backend state through `getBiaiceClient()` and pass the resulting props
 * to the page block. They never render fake data; failures bubble up to
 * the global error boundary as RFC 7807 problems.
 */

import BaselineScenariosBlock from "./baseline-scenarios";
import EligibilityBlock from "./eligibility";
import SimulationBlock from "./simulation";

/**
 * MFA state is propagated by member 1's session loader; the simulation
 * feature only consumes it to gate freeze / cancel / retry / publish
 * actions. We never re-validate MFA in this file.
 *
 * Every field is optional because member 1's `units/[unitId]/{baseline-scenarios,
 * simulation, eligibility}/page.tsx` files render the mounts without arguments
 * (the layout supplies project/unit identifiers through the React tree rather
 * than as direct call arguments). The Mount components accept the optional
 * shape and forward sensible defaults — `unitId` falls back to an empty
 * string that the backend will reject as a Problem, and `mfaVerified` defaults
 * to false so the gate copy renders correctly.
 */
export interface MountProps {
  projectId?: string;
  unitId?: string;
  mfaVerified?: boolean;
}

export async function BaselineScenariosMount({ unitId = "", mfaVerified = false }: MountProps = {}) {
  return <BaselineScenariosBlock unitId={unitId} mfaVerified={mfaVerified} />;
}

export async function SimulationMount({ unitId = "", mfaVerified = false }: MountProps = {}) {
  return <SimulationBlock unitId={unitId} mfaVerified={mfaVerified} />;
}

export async function EligibilityMount({ unitId = "", mfaVerified = false }: MountProps = {}) {
  return <EligibilityBlock unitId={unitId} mfaVerified={mfaVerified} />;
}

/* Default exports for member 1 if it prefers named imports per-mount. */
export default {
  BaselineScenariosMount,
  SimulationMount,
  EligibilityMount,
} as const;
