import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FeaturePlaceholder } from "@/components/shell";

describe("FeaturePlaceholder", () => {
  it("identifies ownership and never presents the mount as completed business", () => {
    render(
      <FeaturePlaceholder
        contract="冻结的生成客户端"
        description="静态挂载说明"
        gate="未知状态失败关闭"
        owner={6}
        title="仿真与方案"
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "仿真与方案" })).toBeVisible();
    expect(screen.getByText("成员 6")).toBeVisible();
    expect(screen.getByText("业务尚未接入")).toBeVisible();
    expect(screen.getByText(/没有演示数据/)).toBeVisible();
  });
});
