import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApprovalsMount } from "@/features/approvals/public";
import * as api from "@/features/approvals/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "project-1", unitId: "unit-1" }),
}));

vi.mock("@/features/approvals/api", () => ({
  listRiskAcceptances: vi.fn(),
  getCurrentIdentity: vi.fn(),
  createRiskAcceptance: vi.fn(),
  revokeRiskAcceptance: vi.fn(),
  newIdempotencyKey: vi.fn((action: string) => `idem-${action}`),
}));

const mockedApi = vi.mocked(api);

function riskAcceptance() {
  return {
    risk_acceptance_id: "ra-1",
    version_id: "version-1",
    tenant_id: "tenant-1",
    data_domain_id: "domain-1",
    decision_unit_id: "unit-1",
    state: "ACTIVE" as const,
    validity: "CURRENT" as const,
    risk: "场景 CVaR 超限风险",
    metric: "Scenario CVaR",
    acceptance_scope: "unit bid",
    rationale: "independent approver accepted",
    independent_approver_id: "approver-1",
    valid_from: "2026-08-18T00:00:00Z",
    valid_until: "2026-09-18T00:00:00Z",
    created_at: "2026-08-18T00:00:00Z",
    created_by: "maker-1",
    accepted_at: "2026-08-18T00:00:00Z",
    accepted_by: "approver-1",
  };
}

function meResponse(mfaVerified: boolean) {
  return {
    subject_id: "subject-1",
    username: "m7",
    display_name: "Member Seven",
    tenant_id: "tenant-1",
    data_domain_id: "domain-1",
    roles: ["REPORT_MANAGER"],
    permissions: [],
    mfa_verified: mfaVerified,
    authenticated_at: "2026-08-18T00:00:00Z",
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ApprovalsMount", () => {
  it("shows the risk acceptance boundary and current record", async () => {
    mockedApi.listRiskAcceptances.mockResolvedValue([riskAcceptance()]);
    mockedApi.getCurrentIdentity.mockResolvedValue(meResponse(true));

    render(<ApprovalsMount />);

    expect(screen.getByRole("heading", { level: 1, name: "审批与风险接受" })).toBeVisible();
    expect(screen.getByText("Pilot 前关闭审批")).toBeVisible();
    expect(await screen.findByText("场景 CVaR 超限风险")).toBeVisible();
    expect(screen.getByRole("button", { name: "创建风险接受" })).toBeEnabled();
  });

  it("disables writes and explains the MFA requirement", async () => {
    mockedApi.listRiskAcceptances.mockResolvedValue([]);
    mockedApi.getCurrentIdentity.mockResolvedValue(meResponse(false));

    render(<ApprovalsMount />);

    expect(await screen.findByText("还没有风险接受")).toBeVisible();
    expect(screen.getByText(/创建与撤销都需要当前会话完成 MFA/)).toBeVisible();
    expect(screen.getByRole("button", { name: "创建风险接受" })).toBeDisabled();
  });
});
