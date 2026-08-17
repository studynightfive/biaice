import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScopeRulesMount } from "@/features/rules/public";

describe("member-2 rules surface", () => {
  it("shows empty published records and conflict/blocking boundaries", () => {
    render(<ScopeRulesMount />);
    expect(screen.getByRole("heading", { level: 1, name: "制度、范围与规则" })).toBeVisible();
    expect(screen.getByText("冲突必须人工确认")).toBeVisible();
    expect(screen.getByText("跨标段与多轮只阻断")).toBeVisible();
    expect(screen.getByRole("heading", { name: "范围评估" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "合规复核" })).toBeVisible();
    expect(screen.getAllByText("暂无已发布记录").length).toBe(4);
  });
});
