import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProjectListMount, UnitOverviewMount } from "@/features/projects/public";

describe("member-2 project surfaces", () => {
  it("keeps the project list empty and never presents a default GO", () => {
    render(<ProjectListMount />);
    expect(screen.getByRole("heading", { level: 1, name: "项目列表" })).toBeVisible();
    expect(screen.getByText("未接入真实租户数据")).toBeVisible();
    expect(screen.getByText("不显示默认 GO 或演示结论")).toBeVisible();
    expect(screen.getAllByText("当前范围无可显示记录").length).toBeGreaterThan(0);
  });

  it("shows lifecycle as member-2 owned and fail-closed when the unit is missing", () => {
    render(<UnitOverviewMount />);
    expect(screen.getByRole("heading", { level: 1, name: "决策单元概览" })).toBeVisible();
    expect(screen.getByText(/生命周期唯一 writer/)).toBeVisible();
    expect(screen.getByText(/不能显示 GO/)).toBeVisible();
  });
});
