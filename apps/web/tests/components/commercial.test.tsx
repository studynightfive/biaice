import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CommercialReadinessMount } from "@/features/commercial/public";

vi.mock("next/navigation", () => ({
  useParams: () => ({ projectId: "project-1", unitId: "unit-1" }),
}));

describe("CommercialReadinessMount", () => {
  it("keeps commercial refusal separate from tender invalidity", () => {
    render(<CommercialReadinessMount />);

    expect(screen.getByRole("heading", { level: 1, name: "成本、政策与就绪" })).toBeVisible();
    expect(screen.getByText("语义分离")).toBeVisible();
    expect(screen.getByText(/不能写成采购规则意义上的投标无效/)).toBeVisible();
  });
});
