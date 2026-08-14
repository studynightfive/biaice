import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccessAuditMount } from "@/features/access-audit/public";

describe("AccessAuditMount", () => {
  it("shows every member-1 governance surface and the audit fail-closed boundary", () => {
    render(<AccessAuditMount />);

    expect(screen.getByRole("heading", { level: 1, name: "访问、审计与数据处置" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "审计事件与完整性" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "血缘与失效传播" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "保留与法务保全" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "删除编排与墓碑" })).toBeVisible();
    expect(screen.getByText("敏感操作必须失败关闭")).toBeVisible();
  });
});
