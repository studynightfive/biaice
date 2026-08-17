/** Same-origin BFF client matching generated BiaiceClient JSON behaviour. */

export class DocumentsProblem extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.status = status;
    this.code = code;
  }
}

export type SourceDocument = {
  readonly document_id: string;
  readonly kind: string;
  readonly name: string;
  readonly status: string;
  readonly scan_result: string;
  readonly content_hash: string;
  readonly sniffed_content_type: string;
  readonly mime_category: string;
  readonly size_bytes: number;
  readonly uploaded_at: string;
};

export type DocumentListResponse = { readonly items: ReadonlyArray<SourceDocument> };

export type UploadSessionResponse = {
  readonly session_id: string;
  readonly status: string;
  readonly next_action: string;
  readonly missing_part_numbers: ReadonlyArray<number>;
  readonly chunk_size_bytes: number;
  readonly total_parts: number;
  readonly document_id: string | null;
};

export type CompleteUploadResponse = {
  readonly session: UploadSessionResponse;
  readonly document: SourceDocument;
};

export type ParseJobResponse = {
  readonly parse_job_id: string;
  readonly document_id: string;
  readonly status: string;
  readonly stage: string | null;
  readonly progress_percent: number;
  readonly retryable: string | null;
  readonly failure_detail: string | null;
};

type RequestOptions = {
  readonly path?: Readonly<Record<string, string>>;
  readonly body?: unknown;
  readonly idempotencyKey?: string;
  readonly signal?: AbortSignal;
};

function newIdempotencyKey(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

async function requestJson<T>(method: string, template: string, options: RequestOptions = {}): Promise<T> {
  const path = template.replace(/\{([^}]+)\}/g, (_, key: string) => {
    const value = options.path?.[key];
    if (value === undefined) throw new Error(`Missing path parameter: ${key}`);
    return encodeURIComponent(value);
  });
  const headers = new Headers({ Accept: "application/json, application/problem+json" });
  if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(path, {
    method,
    credentials: "include",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  if (!response.ok) {
    const problem = (await response.json()) as { code?: string; detail?: string };
    throw new DocumentsProblem(response.status, problem.code ?? "INTERNAL_ERROR", problem.detail ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function listUnitDocuments(unitId: string, signal?: AbortSignal) {
  return requestJson<DocumentListResponse>("GET", "/api/v1/decision-units/{unit_id}/documents", {
    path: { unit_id: unitId },
    signal,
  });
}

export function createUnitUploadSession(
  unitId: string,
  body: {
    filename: string;
    file_size_bytes: number;
    declared_sha256: string;
    content_type: string;
    kind: string;
    chunk_size_bytes: number;
  },
) {
  return requestJson<UploadSessionResponse>("POST", "/api/v1/decision-units/{unit_id}/document-upload-sessions", {
    path: { unit_id: unitId },
    body,
    idempotencyKey: newIdempotencyKey("upload-session"),
  });
}

export async function putUploadChunk(sessionId: string, partNumber: number, data: ArrayBuffer, sha256: string) {
  const headers = new Headers({
    Accept: "application/json, application/problem+json",
    "Content-Type": "application/octet-stream",
    "Idempotency-Key": newIdempotencyKey("chunk"),
    "X-Content-SHA256": sha256,
  });
  const response = await fetch(
    `/api/v1/document-upload-sessions/${encodeURIComponent(sessionId)}/chunks/${partNumber}`,
    { method: "PUT", credentials: "include", headers, body: data },
  );
  if (!response.ok) {
    const problem = (await response.json()) as { code?: string; detail?: string };
    throw new DocumentsProblem(response.status, problem.code ?? "INTERNAL_ERROR", problem.detail ?? response.statusText);
  }
  return (await response.json()) as UploadSessionResponse;
}

export function completeUploadSession(sessionId: string) {
  return requestJson<CompleteUploadResponse>("POST", "/api/v1/document-upload-sessions/{session_id}/complete", {
    path: { session_id: sessionId },
    idempotencyKey: newIdempotencyKey("complete"),
  });
}

export function createUnitParseJob(unitId: string, documentId: string) {
  return requestJson<ParseJobResponse>("POST", "/api/v1/decision-units/{unit_id}/parse-jobs", {
    path: { unit_id: unitId },
    body: { document_id: documentId },
    idempotencyKey: newIdempotencyKey("parse"),
  });
}

export function getParseJob(parseJobId: string, signal?: AbortSignal) {
  return requestJson<ParseJobResponse>("GET", "/api/v1/parse-jobs/{parse_job_id}", {
    path: { parse_job_id: parseJobId },
    signal,
  });
}

export async function sha256Hex(data: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
