import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createBatch,
  createSearchSpace,
  getCurrentIdentity,
  listDecisionBaselines,
  loadBaselineBundle,
} from "@/features/simulation/api";
import {
  __setBiaiceClient,
  type BiaiceClient,
  type BiaiceRequestOptions,
} from "@/lib/api/client";

function mockClient(
  implementation: (
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    options?: BiaiceRequestOptions,
  ) => Promise<unknown>,
): BiaiceClient {
  return { request: vi.fn(implementation) as BiaiceClient["request"] };
}

afterEach(() => {
  __setBiaiceClient(undefined);
  vi.unstubAllGlobals();
});

describe("simulation API contract adapters", () => {
  it("unwraps list envelopes instead of treating the envelope as an array", async () => {
    const baseline = { baseline_id: "baseline-1", state: "FROZEN" };
    const client = mockClient(async () => ({ items: [baseline] }));
    __setBiaiceClient(client);

    await expect(listDecisionBaselines("unit/a")).resolves.toEqual([baseline]);
    expect(client.request).toHaveBeenCalledWith(
      "GET",
      "/api/v1/decision-units/unit%2Fa/decision-baselines",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("sends the frozen CreateSearchSpaceRequest field names", async () => {
    const client = mockClient(async () => ({ search_space_id: "space-1" }));
    __setBiaiceClient(client);
    const body = {
      decision_unit_id: "unit-1",
      baseline_id: "baseline-1",
      description: "price and quality",
      dimension_axes: ["price", "quality"],
      candidate_count_lower_bound: 2,
    } as const;

    await createSearchSpace("unit-1", body, "idem-search");

    expect(client.request).toHaveBeenCalledWith(
      "POST",
      "/api/v1/decision-units/unit-1/candidate-search-spaces",
      expect.objectContaining({ body, idempotencyKey: "idem-search" }),
    );
  });

  it("sends the batch's baseline, scenario, award mode and threshold", async () => {
    const client = mockClient(async () => ({ batch_id: "batch-1" }));
    __setBiaiceClient(client);
    const body = {
      decision_unit_id: "unit-1",
      baseline_id: "baseline-1",
      scenario_set_id: "scenario-1",
      award_mode: "SINGLE" as const,
      policy_threshold: "0.5",
    };

    await createBatch("unit-1", body, "idem-batch");

    expect(client.request).toHaveBeenCalledWith(
      "POST",
      "/api/v1/decision-units/unit-1/simulation-batches",
      expect.objectContaining({ body, idempotencyKey: "idem-batch" }),
    );
  });

  it("builds a baseline bundle from all three list envelopes", async () => {
    const frozen = { baseline_id: "current", state: "FROZEN" };
    const superseded = { baseline_id: "old", state: "SUPERSEDED" };
    const client = mockClient(async (_method, path) => {
      if (path.endsWith("decision-baselines")) return { items: [frozen, superseded] };
      if (path.endsWith("candidate-search-spaces")) return { items: [{ search_space_id: "s" }] };
      if (path.endsWith("scenario-sets")) return { items: [{ scenario_set_id: "x" }] };
      throw new Error(`Unexpected path: ${path}`);
    });
    __setBiaiceClient(client);

    const bundle = await loadBaselineBundle("unit-1");

    expect(bundle.current).toBe(frozen);
    expect(bundle.superseded).toEqual([superseded]);
    expect(bundle.readiness).toEqual({ status: "READY", reasonCodes: [] });
  });

  it("uses the same-origin BFF and includes HttpOnly session credentials", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ mfa_verified: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await getCurrentIdentity();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/me",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });
});
