import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRiskAcceptance,
  getCurrentIdentity,
  listRiskAcceptances,
  revokeRiskAcceptance,
} from "@/features/approvals/api";
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
});

describe("approvals API contract adapters", () => {
  it("unwraps the risk acceptance list envelope", async () => {
    const item = { risk_acceptance_id: "ra-1", state: "ACTIVE", validity: "CURRENT" };
    const client = mockClient(async () => ({ items: [item] }));
    __setBiaiceClient(client);

    await expect(listRiskAcceptances("unit/a")).resolves.toEqual([item]);
    expect(client.request).toHaveBeenCalledWith(
      "GET",
      "/api/v1/decision-units/unit%2Fa/risk-acceptances",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("sends the frozen CreateRiskAcceptanceRequest field names", async () => {
    const client = mockClient(async () => ({ risk_acceptance_id: "ra-2" }));
    __setBiaiceClient(client);
    const body = {
      risk: "scenario cvar",
      metric: "Scenario CVaR",
      acceptance_scope: "unit bid",
      rationale: "independent approver accepted",
      independent_approver_id: "approver-1",
      valid_from: "2026-08-18T00:00:00Z",
      valid_until: "2026-09-18T00:00:00Z",
    };

    await createRiskAcceptance("unit-1", body, "idem-create");

    expect(client.request).toHaveBeenCalledWith(
      "POST",
      "/api/v1/decision-units/unit-1/risk-acceptances",
      expect.objectContaining({ body, idempotencyKey: "idem-create" }),
    );
  });

  it("sends the revoke reason and idempotency key", async () => {
    const client = mockClient(async () => ({ risk_acceptance_id: "ra-3", state: "REVOKED" }));
    __setBiaiceClient(client);

    await revokeRiskAcceptance("ra-3", { revocation_reason: "upstream changed" }, "idem-revoke");

    expect(client.request).toHaveBeenCalledWith(
      "POST",
      "/api/v1/risk-acceptances/ra-3/revoke",
      expect.objectContaining({
        body: { revocation_reason: "upstream changed" },
        idempotencyKey: "idem-revoke",
      }),
    );
  });

  it("reads the current identity for the MFA gate", async () => {
    const client = mockClient(async () => ({ mfa_verified: true }));
    __setBiaiceClient(client);

    await expect(getCurrentIdentity()).resolves.toEqual({ mfa_verified: true });
    expect(client.request).toHaveBeenCalledWith(
      "GET",
      "/api/v1/me",
      expect.objectContaining({ cache: "no-store" }),
    );
  });
});

