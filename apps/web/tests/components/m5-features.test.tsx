import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MarketMount } from "@/features/market/public";
import {
  AiProviderSettingsMount,
  PrivacyModelsMount,
} from "@/features/privacy-models/public";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("member 5 feature mounts", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("crypto", {
      randomUUID: vi.fn(() => "00000000-0000-4000-8000-000000000501"),
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("creates a competitor through the real FR-05 route", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(200, { items: [] }))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          competitor_id: "00000000-0000-4000-8000-000000000511",
          legal_name: "合成竞对甲",
          canonical_subject_key: "合成竞对甲",
          aliases: ["竞对甲"],
          archived_at: null,
        }),
      );

    render(<MarketMount />);
    expect(await screen.findByText("暂无竞对")).toBeVisible();
    fireEvent.change(screen.getByLabelText("法定名称"), {
      target: { value: "合成竞对甲" },
    });
    fireEvent.change(screen.getByLabelText("别名"), {
      target: { value: "竞对甲" },
    });
    const createButton = screen.getByRole("button", { name: "创建竞对" });
    expect(createButton).toBeEnabled();
    fireEvent.click(createButton);

    expect(await screen.findByText("竞对草稿已创建")).toBeVisible();
    const [, init] = vi.mocked(fetch).mock.calls.at(-1) ?? [];
    expect(init).toEqual(expect.objectContaining({ method: "POST" }));
    expect(new Headers(init?.headers).get("Idempotency-Key")).toContain("competitor-");
  });

  it("enables FR-12 synthetic writes and sends the frozen command envelope", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(200, { items: [], has_more: false, next_cursor: null }),
      )
      .mockResolvedValueOnce(
        jsonResponse(200, {
          resource_id: "00000000-0000-4000-8000-000000000521",
          resource_type: "processing_record",
          state: "DRAFT",
          state_version: 1,
          updated_at: "2026-08-17T00:00:00Z",
        }),
      );

    render(<PrivacyModelsMount />);
    expect(await screen.findByText("暂无记录")).toBeVisible();
    const createButton = screen.getByRole("button", { name: "创建处理活动记录" });
    expect(createButton).toBeEnabled();
    fireEvent.click(createButton);

    expect(await screen.findByText("处理活动记录已创建")).toBeVisible();
    const [, init] = vi.mocked(fetch).mock.calls.at(-1) ?? [];
    expect(init).toEqual(expect.objectContaining({ method: "POST" }));
    expect(JSON.parse(String(init?.body))).toEqual({
      subject_scope: "synthetic-ui",
      justification_ref: "ui://fr12/manual-entry",
      retention_days: 30,
    });
  });

  it("keeps protected BYOK actions disabled when the public gate is not pass/current", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, {
        status: "UNKNOWN",
        validity: "STALE",
        expires_at: "2026-08-16T00:00:00Z",
        reason_codes: ["MACHINE_ASSESSMENT_MISSING"],
      }),
    );

    render(<AiProviderSettingsMount />);
    expect(await screen.findByText("BYOK BLOCKED")).toBeVisible();
    fireEvent.change(screen.getByLabelText("配置 ID"), {
      target: { value: "00000000-0000-4000-8000-000000000531" },
    });

    expect(screen.getByLabelText("新 API Key（只写）")).toBeDisabled();
    expect(screen.getByRole("button", { name: "创建轮换后继版本" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "固定载荷连接测试" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "激活配置" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "暂停配置" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "撤销配置" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "紧急撤销 Key" })).toBeEnabled();
  });

  it("enables protected BYOK actions only for a non-expired pass/current gate", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(200, {
          status: "PASS",
          validity: "CURRENT",
          expires_at: "2999-08-17T00:00:00Z",
          reason_codes: [],
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, {}))
      .mockResolvedValueOnce(jsonResponse(200, {}));

    render(<AiProviderSettingsMount />);
    expect(await screen.findByText("BYOK PASS/CURRENT")).toBeVisible();
    fireEvent.change(screen.getByLabelText("配置 ID"), {
      target: { value: "00000000-0000-4000-8000-000000000541" },
    });
    fireEvent.change(screen.getByLabelText("新 API Key（只写）"), {
      target: { value: "test-secret-never-render" },
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "创建轮换后继版本" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "写入新 Key" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "固定载荷连接测试" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "激活配置" })).toBeEnabled();
    });
    expect(screen.queryByText("test-secret-never-render")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "创建轮换后继版本" }));
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2));
    let [, init] = vi.mocked(fetch).mock.calls.at(-1) ?? [];
    expect(JSON.parse(String(init?.body))).toEqual({
      rotation_mode: "PLANNED",
      reason_code: "USER_REQUESTED_ROTATION",
    });

    await waitFor(() => expect(screen.getByRole("button", { name: "激活配置" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "激活配置" }));
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3));
    [, init] = vi.mocked(fetch).mock.calls.at(-1) ?? [];
    expect(JSON.parse(String(init?.body))).toEqual({
      reason_code: "USER_REQUESTED_ACTIVATE",
    });
  });
});
