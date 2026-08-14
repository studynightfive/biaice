import { type NextRequest, NextResponse } from "next/server";
import { BffConfigurationError, readBffConfig, type BffConfig } from "./config";
import {
  clearSessionCookies,
  readSessionCookies,
  setSessionCookies,
  type CurrentSessionCookies,
} from "./cookies";
import { configurationProblem, problemResponse } from "./problem";
import {
  ACCESS_REFRESH_WINDOW_SECONDS,
  isSameOriginMutation,
  readJwtExpiration,
} from "./security";
import { OidcProviderError, refreshAccessToken, type TokenSet } from "./tokens";

const REQUEST_HEADERS_TO_REMOVE = new Set([
  "authorization",
  "connection",
  "content-length",
  "cookie",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "set-cookie",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-port",
  "x-forwarded-proto",
]);

const RESPONSE_HEADERS_TO_REMOVE = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "set-cookie",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

const EXACT_SCOPE_HEADERS = new Set([
  "x-tenant-id",
  "x-data-domain-id",
  "x-project-id",
  "x-project-scope",
  "x-decision-unit-id",
  "x-unit-scope",
  "x-scope",
]);

type ApiRouteContext = {
  params: Promise<{ path: string[] }>;
};

type FetchRequestInit = RequestInit & { duplex?: "half" };

type SessionResolution =
  | { kind: "ready"; accessToken: string; current: CurrentSessionCookies; refreshed?: TokenSet }
  | { kind: "missing" }
  | { kind: "invalid" };

function isScopeHeader(name: string): boolean {
  return (
    EXACT_SCOPE_HEADERS.has(name) ||
    name.startsWith("x-scope-") ||
    name.startsWith("x-biaice-scope-") ||
    name.endsWith("-scope")
  );
}

function buildUpstreamHeaders(request: NextRequest, config: BffConfig, accessToken: string): Headers {
  const headers = new Headers(request.headers);
  for (const name of [...headers.keys()]) {
    const normalized = name.toLowerCase();
    if (REQUEST_HEADERS_TO_REMOVE.has(normalized) || isScopeHeader(normalized)) {
      headers.delete(name);
    }
  }
  const publicUrl = new URL(config.publicOrigin);
  headers.set("Authorization", `Bearer ${accessToken}`);
  headers.set("Accept-Encoding", "identity");
  headers.set("X-Forwarded-Host", publicUrl.host);
  headers.set("X-Forwarded-Proto", publicUrl.protocol.slice(0, -1));
  headers.set("X-Forwarded-Port", publicUrl.port || (publicUrl.protocol === "https:" ? "443" : "80"));
  return headers;
}

function buildDownstreamHeaders(upstream: Headers): Headers {
  const headers = new Headers(upstream);
  for (const name of [...headers.keys()]) {
    if (RESPONSE_HEADERS_TO_REMOVE.has(name.toLowerCase())) headers.delete(name);
  }
  headers.set("Cache-Control", "no-store");
  headers.set("X-Content-Type-Options", "nosniff");
  return headers;
}

async function resolveSession(
  request: NextRequest,
  config: BffConfig,
): Promise<SessionResolution> {
  const current = readSessionCookies(request);
  const expiration = readJwtExpiration(current.accessToken);
  const now = Math.floor(Date.now() / 1000);
  if (current.accessToken && expiration && expiration > now + ACCESS_REFRESH_WINDOW_SECONDS) {
    return { kind: "ready", accessToken: current.accessToken, current };
  }
  if (!current.refreshToken) return { kind: "missing" };

  try {
    const refreshed = await refreshAccessToken(config, current.refreshToken);
    return {
      kind: "ready",
      accessToken: refreshed.accessToken,
      current,
      refreshed,
    };
  } catch {
    return { kind: "invalid" };
  }
}

function buildUpstreamUrl(config: BffConfig, request: NextRequest, path: string[]): URL {
  const encodedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const upstream = new URL(`${config.apiInternalUrl}/api/v1/${encodedPath}`);
  upstream.search = request.nextUrl.search;
  return upstream;
}

export async function proxyApiRequest(
  request: NextRequest,
  context: ApiRouteContext,
): Promise<NextResponse> {
  let config: BffConfig;
  try {
    config = readBffConfig();
  } catch (error) {
    if (error instanceof BffConfigurationError) return configurationProblem(request);
    throw error;
  }

  if (!isSameOriginMutation(request, config)) {
    return problemResponse(
      request,
      403,
      "CROSS_SITE_REQUEST_FORBIDDEN",
      "Cross-site request forbidden",
      "State-changing API requests require the configured same-origin browser context.",
    );
  }

  const session = await resolveSession(request, config);
  if (session.kind !== "ready") {
    const response = problemResponse(
      request,
      401,
      session.kind === "missing" ? "AUTH_REQUIRED" : "TOKEN_INVALID",
      "Authentication required",
      "Sign in with the local identity provider and retry.",
    );
    if (session.kind === "invalid") clearSessionCookies(response, config);
    return response;
  }

  const { path } = await context.params;
  if (!path.length || path.some((segment) => segment === "." || segment === "..")) {
    return problemResponse(
      request,
      400,
      "INVALID_API_PATH",
      "Invalid API path",
      "The proxied API path contains an invalid segment.",
    );
  }
  const upstreamUrl = buildUpstreamUrl(config, request, path);
  const init: FetchRequestInit = {
    method: request.method,
    headers: buildUpstreamHeaders(request, config, session.accessToken),
    cache: "no-store",
    redirect: "manual",
    signal: request.signal,
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, init);
  } catch (error) {
    if (error instanceof OidcProviderError) {
      const response = problemResponse(
        request,
        401,
        "TOKEN_INVALID",
        "Authentication required",
        "The local identity session is no longer valid. Sign in again.",
      );
      clearSessionCookies(response, config);
      return response;
    }
    return problemResponse(
      request,
      502,
      "UPSTREAM_UNAVAILABLE",
      "API unavailable",
      "The local API did not accept the proxied request.",
    );
  }

  const responseHasNoBody =
    request.method === "HEAD" || [204, 205, 304].includes(upstreamResponse.status);
  const response = new NextResponse(responseHasNoBody ? null : upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: buildDownstreamHeaders(upstreamResponse.headers),
  });
  if (session.refreshed) {
    setSessionCookies(response, config, session.refreshed, session.current);
  }
  return response;
}
