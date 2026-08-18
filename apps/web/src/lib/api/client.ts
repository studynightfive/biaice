/**
 * Localised BiaiceClient wrapper used by the simulation feature.
 *
 * The real client is generated into `packages/contracts/generated-typescript`
 * by member 1 from the OpenAPI document. Member 6 is not allowed to vendor
 * another copy of the generated sources, so we only re-declare the contract
 * surface that the simulation feature actually relies on (a single
 * `request` method) and adapt it to Next.js 16 server-side `fetch`.
 *
 * The wrapper is intentionally thin:
 *   - it forwards the `Idempotency-Key` header required by every write,
 *   - it converts non-2xx responses into a `BiaiceProblem` carrying the
 *     parsed RFC 7807 ProblemDetails payload,
 *   - it never swallows or rewrites the body, so React error boundaries
 *     receive an authentic failure object.
 */


export interface BiaiceRequestOptions {
  /** Request body for write operations. Must already be JSON-serialisable. */
  body?: unknown;
  /**
   * Required by the operation catalog for any non-GET request. The caller is
   * responsible for generating a stable key (we never re-generate one here
   * because that would silently turn a duplicate write into a fresh request).
   */
  idempotencyKey?: string;
  /** Optional ETag for conditional reads. */
  ifNoneMatch?: string;
  /** Extra query string parameters merged into the URL. */
  query?: Record<string, string | number | boolean | undefined>;
  /**
   * Cache policy. The simulation feature must always observe the latest
   * backend state — never a stale one — so callers pass
   * `{ cache: "no-store", next: { revalidate: 0 } }`.
   */
  cache?: RequestCache;
  next?: { revalidate?: number; tags?: string[] };
}

export interface BiaiceProblem extends Error {
  /** HTTP status code returned by the API. */
  status: number;
  /** Stable RFC 7807 type URI, when the API provides one. */
  type?: string;
  /** Short, human-readable summary. */
  title?: string;
  /** Optional code that is more specific than the HTTP status. */
  code?: string;
  /** The parsed ProblemDetails object, when available. */
  details?: unknown;
}

// Browser calls must stay on the same origin so the BFF can attach the
// HttpOnly OIDC session. The browser must never call the backend directly.
const DEFAULT_BASE = "";

function buildProblem(
  status: number,
  payload: unknown,
  fallback: string,
): BiaiceProblem {
  const detail =
    typeof payload === "object" && payload !== null
      ? (payload as { detail?: unknown }).detail
      : undefined;
  const message = typeof detail === "string" && detail ? detail : fallback;
  const problem: BiaiceProblem = Object.assign(new Error(message), {
    name: "BiaiceProblem",
    status,
    type: typeof payload === "object" && payload !== null
      ? (payload as { type?: string }).type
      : undefined,
    title: typeof payload === "object" && payload !== null
      ? (payload as { title?: string }).title
      : undefined,
    code: typeof payload === "object" && payload !== null
      ? (payload as { code?: string }).code
      : undefined,
    details: payload,
  });
  return problem;
}

function appendQuery(
  url: string,
  query?: BiaiceRequestOptions["query"],
): string {
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue;
    params.set(key, String(value));
  }
  if (Array.from(params).length === 0) return url;
  return url + (url.includes("?") ? "&" : "?") + params.toString();
}

export interface BiaiceClient {
  request<TResponse = unknown>(
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    options?: BiaiceRequestOptions,
  ): Promise<TResponse>;
}

class HttpBiaiceClient implements BiaiceClient {
  private readonly base: string;

  constructor(base: string) {
    this.base = base.replace(/\/$/, "");
  }

  async request<TResponse>(
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    options: BiaiceRequestOptions = {},
  ): Promise<TResponse> {
    const url = appendQuery(this.base + path, options.query);
    const headers: Record<string, string> = {
      Accept: "application/json, application/problem+json",
    };
    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    if (options.idempotencyKey) {
      headers["Idempotency-Key"] = options.idempotencyKey;
    }
    if (options.ifNoneMatch) {
      headers["If-None-Match"] = options.ifNoneMatch;
    }

    const response = await fetch(url, {
      method,
      credentials: "include",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: options.cache ?? "no-store",
      // Always revalidate so the simulation page reflects the most recent
      // baseline / batch / eligibility state.
      next: options.next ?? { revalidate: 0 },
    });

    if (response.status === 204) {
      return undefined as TResponse;
    }

    const text = await response.text();
    let parsed: unknown = undefined;
    if (text.length > 0) {
      try {
        parsed = JSON.parse(text);
      } catch {
        parsed = text;
      }
    }

    if (!response.ok) {
      throw buildProblem(response.status, parsed, response.statusText);
    }

    return parsed as TResponse;
  }
}

let cached: BiaiceClient | undefined;

/**
 * Returns the shared BiaiceClient. The instance is created lazily and cached
 * per process so that we never rebuild the underlying `fetch` configuration.
 */
export function getBiaiceClient(): BiaiceClient {
  if (!cached) {
    cached = new HttpBiaiceClient(DEFAULT_BASE);
  }
  return cached;
}

/** Exposed for tests that need to swap the implementation. */
export function __setBiaiceClient(client: BiaiceClient | undefined): void {
  cached = client;
}
