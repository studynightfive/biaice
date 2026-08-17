import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentsMount } from "@/features/documents/public";

vi.mock("next/navigation", () => ({
  useParams: () => ({
    projectId: "00000000-0000-4000-8000-000000000201",
    unitId: "00000000-0000-4000-8000-000000000202",
  }),
}));

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("DocumentsMount", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows loading then the empty intake state", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      await jsonResponse(200, { items: [] }),
    );
    render(<DocumentsMount />);
    expect(screen.getByText("正在读取资料清单")).toBeVisible();
    expect(await screen.findByText("暂无已摄入资料")).toBeVisible();
    expect(screen.getByLabelText("选择要摄入的文件")).toBeVisible();
  });

  it("renders ingested documents in the normal state", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      await jsonResponse(200, {
        items: [
          {
            document_id: "00000000-0000-4000-8000-000000000301",
            kind: "TENDER",
            name: "tender.pdf",
            status: "SCAN_PASSED",
            scan_result: "CLEAN",
            content_hash: "a".repeat(64),
            sniffed_content_type: "application/pdf",
            mime_category: "PDF",
            size_bytes: 12,
            uploaded_at: "2026-08-17T00:00:00+00:00",
          },
        ],
      }),
    );
    render(<DocumentsMount />);
    expect(await screen.findByText("tender.pdf")).toBeVisible();
    expect(screen.getByText("SCAN_PASSED")).toBeVisible();
    expect(screen.getByRole("link", { name: "下载" })).toBeVisible();
  });

  it("shows unauthorized, expired and error states from problem responses", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      await jsonResponse(403, {
        code: "PERMISSION_DENIED",
        detail: "missing fr-02:read",
      }),
    );
    const first = render(<DocumentsMount />);
    expect(await screen.findByText("当前身份无权访问资料")).toBeVisible();
    first.unmount();

    vi.mocked(fetch).mockResolvedValueOnce(
      await jsonResponse(410, {
        code: "UPLOAD_SESSION_EXPIRED",
        detail: "session expired",
      }),
    );
    const second = render(<DocumentsMount />);
    expect(await screen.findByText("上传会话已过期")).toBeVisible();
    second.unmount();

    vi.mocked(fetch).mockResolvedValueOnce(
      await jsonResponse(500, { code: "INTERNAL_ERROR", detail: "boom" }),
    );
    render(<DocumentsMount />);
    await waitFor(() => expect(screen.getByText("资料服务返回错误")).toBeVisible());
  });
});
