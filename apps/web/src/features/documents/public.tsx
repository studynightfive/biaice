"use client";

import { useCallback, useEffect, useState, type ChangeEvent } from "react";
import { useParams } from "next/navigation";
import { Button, Card, EmptyState, LinkButton, Notice, StatusBadge } from "@/components/ui";
import {
  DocumentsProblem,
  completeUploadSession,
  createUnitParseJob,
  createUnitUploadSession,
  getParseJob,
  listUnitDocuments,
  putUploadChunk,
  sha256Hex,
  type ParseJobResponse,
  type SourceDocument,
} from "./api";
import styles from "./documents.module.css";

const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;
const TERMINAL_PARSE = new Set(["SUCCEEDED", "FAILED", "CANCELLED"]);

type PageState = "loading" | "empty" | "ready" | "unauthorized" | "expired" | "error";

function statusTone(status: string): "success" | "warning" | "critical" | "info" {
  if (status === "RELEASED" || status === "SCAN_PASSED" || status === "SUCCEEDED") return "success";
  if (status === "SCAN_FAILED" || status === "QUARANTINED" || status === "FAILED") return "critical";
  if (status === "EXPIRED") return "warning";
  return "info";
}

function classifyError(error: unknown): PageState {
  if (error instanceof DocumentsProblem) {
    if (error.status === 401 || error.status === 403) return "unauthorized";
    if (error.status === 410 || error.code === "UPLOAD_SESSION_EXPIRED") return "expired";
  }
  return "error";
}

export function DocumentsMount() {
  const params = useParams<{ projectId: string; unitId: string }>();
  const unitId = params.unitId;
  const [state, setState] = useState<PageState>("loading");
  const [errorDetail, setErrorDetail] = useState("资料服务暂时不可用。");
  const [documents, setDocuments] = useState<ReadonlyArray<SourceDocument>>([]);
  const [parseJobs, setParseJobs] = useState<Record<string, ParseJobResponse>>({});
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!unitId) return;
      const result = await listUnitDocuments(unitId, signal);
      setDocuments(result.items);
      setState(result.items.length === 0 ? "empty" : "ready");
    },
    [unitId],
  );

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setErrorDetail(error instanceof Error ? error.message : "资料服务暂时不可用。");
      setState(classifyError(error));
    });
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    const active = Object.values(parseJobs).filter((job) => !TERMINAL_PARSE.has(job.status));
    if (active.length === 0) return undefined;
    const timer = window.setInterval(() => {
      void Promise.all(
        active.map(async (job) => {
          const latest = await getParseJob(job.parse_job_id);
          setParseJobs((current) => ({ ...current, [latest.document_id]: latest }));
        }),
      );
    }, 1500);
    return () => window.clearInterval(timer);
  }, [parseJobs]);

  async function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !unitId) return;
    setBusy(true);
    try {
      const buffer = await file.arrayBuffer();
      const digest = await sha256Hex(buffer);
      const session = await createUnitUploadSession(unitId, {
        filename: file.name,
        file_size_bytes: file.size,
        declared_sha256: digest,
        content_type: file.type || "application/octet-stream",
        kind: "TENDER",
        chunk_size_bytes: DEFAULT_CHUNK_SIZE,
      });
      for (let part = 1; part <= session.total_parts; part += 1) {
        const start = (part - 1) * session.chunk_size_bytes;
        const end = Math.min(start + session.chunk_size_bytes, file.size);
        const chunk = buffer.slice(start, end);
        await putUploadChunk(session.session_id, part, chunk, await sha256Hex(chunk));
      }
      await completeUploadSession(session.session_id);
      await refresh();
    } catch (error) {
      setErrorDetail(error instanceof Error ? error.message : "上传失败。");
      setState(classifyError(error));
    } finally {
      setBusy(false);
    }
  }

  async function onParse(documentId: string) {
    if (!unitId) return;
    setBusy(true);
    try {
      const job = await createUnitParseJob(unitId, documentId);
      setParseJobs((current) => ({ ...current, [documentId]: job }));
      if (!TERMINAL_PARSE.has(job.status)) {
        const latest = await getParseJob(job.parse_job_id);
        setParseJobs((current) => ({ ...current, [documentId]: latest }));
      }
    } catch (error) {
      setErrorDetail(error instanceof Error ? error.message : "解析失败。");
      setState(classifyError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.page}>
      <Card className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>DOCUMENTS · MEMBER 3</p>
          <h1>资料摄入中心</h1>
          <p>
            招标方、本公司及受控市场资料先隔离、扫描再解析。进度只来自持久化 Job；扫描未通过时禁止查看正文。
          </p>
        </div>
        <StatusBadge tone={state === "ready" ? "success" : "warning"}>
          {state === "ready" ? "已接入真实 API" : "等待资料或授权"}
        </StatusBadge>
      </Card>

      {state === "loading" ? (
        <Notice title="正在读取资料清单" tone="info">
          正在向网关查询当前决策单元的真实文档状态，不会使用前端计时器伪造进度。
        </Notice>
      ) : null}
      {state === "unauthorized" ? (
        <Notice title="当前身份无权访问资料" tone="danger">
          {errorDetail} 需要文档专员、技术负责人或资料管理员角色。
        </Notice>
      ) : null}
      {state === "expired" ? (
        <Notice title="上传会话已过期" tone="warning">
          {errorDetail} 请重新创建上传会话后再传输文件。
        </Notice>
      ) : null}
      {state === "error" ? (
        <Notice title="资料服务返回错误" tone="danger">
          {errorDetail}
        </Notice>
      ) : null}

      {state === "empty" || state === "ready" ? (
        <Card eyebrow="INTAKE" title="上传与解析">
          <div className={styles.toolbar}>
            <input
              aria-label="选择要摄入的文件"
              className={styles.fileInput}
              disabled={busy}
              onChange={onFileChange}
              type="file"
            />
            <StatusBadge tone="info">分块走网关，不直连对象存储</StatusBadge>
          </div>
        </Card>
      ) : null}

      {state === "empty" ? (
        <EmptyState
          description="当前决策单元还没有已摄入资料。上传后会进入隔离扫描，扫描未通过时不会出现可下载正文。"
          title="暂无已摄入资料"
        />
      ) : null}

      {state === "ready" ? (
        <Card eyebrow="REGISTRY" title="已摄入资料">
          <ul className={styles.list}>
            {documents.map((document) => {
              const job = parseJobs[document.document_id];
              const canDownload =
                document.status === "SCAN_PASSED" ||
                document.status === "UNDER_REVIEW" ||
                document.status === "RELEASED";
              return (
                <li className={styles.item} key={document.document_id}>
                  <div>
                    <strong>{document.name}</strong>
                    <small>
                      {document.kind} · {document.content_hash.slice(0, 12)}
                    </small>
                    {job ? (
                      <p className={styles.progress}>
                        解析 Job {job.status} · {job.progress_percent}%
                        {job.failure_detail ? ` · ${job.failure_detail}` : ""}
                      </p>
                    ) : null}
                  </div>
                  <div className={styles.actions}>
                    <StatusBadge tone={statusTone(document.status)}>{document.status}</StatusBadge>
                    {canDownload ? (
                      <LinkButton
                        href={`/api/v1/documents/${encodeURIComponent(document.document_id)}/download`}
                        variant="quiet"
                      >
                        下载
                      </LinkButton>
                    ) : (
                      <StatusBadge tone="critical">禁止查看正文</StatusBadge>
                    )}
                    <Button disabled={busy} onClick={() => void onParse(document.document_id)} variant="secondary">
                      解析
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
