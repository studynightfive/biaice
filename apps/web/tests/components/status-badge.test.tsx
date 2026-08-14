import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/ui";

describe("StatusBadge", () => {
  it("keeps the status available as text instead of color alone", () => {
    render(<StatusBadge tone="critical">访问被阻断</StatusBadge>);

    expect(screen.getByText("访问被阻断")).toBeVisible();
  });
});
