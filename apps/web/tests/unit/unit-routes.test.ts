import { describe, expect, it } from "vitest";
import { buildUnitPath, UNIT_ROUTES } from "@/lib/navigation/unit-routes";

const expectedSuffixes = [
  "/overview",
  "/documents",
  "/scope-rules",
  "/evidence-precheck",
  "/commercial-readiness",
  "/market",
  "/baseline-scenarios",
  "/simulation",
  "/eligibility",
  "/approvals",
  "/reports-submissions",
  "/outcomes",
  "/governance/access-audit",
  "/governance/privacy-models",
];

describe("unit route registry", () => {
  it("contains every frozen decision-unit route exactly once", () => {
    const suffixes = UNIT_ROUTES.map((route) => route.suffix);

    expect(suffixes).toEqual(expectedSuffixes);
    expect(new Set(suffixes).size).toBe(suffixes.length);
  });

  it("records a feature owner and fail-closed gate summary for every route", () => {
    for (const route of UNIT_ROUTES) {
      expect(route.owner).toBeGreaterThanOrEqual(1);
      expect(route.owner).toBeLessThanOrEqual(7);
      expect(route.gateSummary.length).toBeGreaterThan(8);
    }
  });

  it("encodes project and unit identifiers into a local path", () => {
    expect(buildUnitPath("project/alpha", "unit one", "/overview")).toBe(
      "/projects/project%2Falpha/units/unit%20one/overview",
    );
  });
});
