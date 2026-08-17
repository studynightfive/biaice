import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EvidencePrecheckMount } from "@/features/evidence/public";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "project-1", unitId: "unit-1" }),
}));

describe("EvidencePrecheckMount", () => {
  it("shows the fail-closed evidence and precheck boundary", () => {
    render(<EvidencePrecheckMount />);

    expect(screen.getByRole("heading", { level: 1, name: "证据、响应与预审" })).toBeVisible();
    expect(screen.getByText("失败关闭")).toBeVisible();
    expect(screen.getByText(/没有证据不得判满足/)).toBeVisible();
  });
});
