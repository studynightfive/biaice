// @vitest-environment node

import { generateKeyPairSync, sign } from "node:crypto";
import { NextRequest } from "next/server";
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET as beginLogin } from "@/app/api/auth/login/route";
import { GET as completeLogin } from "@/app/api/auth/callback/route";
import { POST as logout } from "@/app/api/auth/logout/route";
import { proxyApiRequest } from "@/server/auth/proxy";
import {
  AUTH_COOKIE_NAMES,
  createCodeChallenge,
  decodeLoginTransaction,
  encodeLoginTransaction,
  type LoginTransaction,
} from "@/server/auth/security";

const REQUIRED_ENVIRONMENT = {
  BIAICE_PUBLIC_ORIGIN: "https://biaice.local:8443",
  BIAICE_OIDC_ISSUER: "https://biaice.local:8443/realms/biaice",
  BIAICE_OIDC_INTERNAL_ISSUER: "http://keycloak:8080/realms/biaice",
  BIAICE_OIDC_CLIENT_ID: "biaice-web",
  API_INTERNAL_URL: "http://api:8000",
};

const environmentNames = Object.keys(REQUIRED_ENVIRONMENT) as Array<
  keyof typeof REQUIRED_ENVIRONMENT
>;
const originalEnvironment = Object.fromEntries(
  environmentNames.map((name) => [name, process.env[name]]),
) as Record<keyof typeof REQUIRED_ENVIRONMENT, string | undefined>;

function configuredRequest(path: string, init?: ConstructorParameters<typeof NextRequest>[1]) {
  return new NextRequest(`${REQUIRED_ENVIRONMENT.BIAICE_PUBLIC_ORIGIN}${path}`, init);
}

function fakeAccessToken(expiration: number): string {
  const encode = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${encode({ alg: "RS256", typ: "JWT" })}.${encode({ exp: expiration })}.signature`;
}

function cookieHeader(values: Record<string, string>): string {
  return Object.entries(values)
    .map(([name, value]) => `${name}=${value}`)
    .join("; ");
}

beforeEach(() => {
  for (const [name, value] of Object.entries(REQUIRED_ENVIRONMENT)) {
    process.env[name] = value;
  }
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

afterAll(() => {
  for (const name of environmentNames) {
    const value = originalEnvironment[name];
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
});

describe("OIDC BFF routes", () => {
  it("replaces an external return_to and emits an S256 transaction", () => {
    const response = beginLogin(
      configuredRequest("/api/auth/login?return_to=https%3A%2F%2Fevil.example%2Fsteal"),
    );

    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.origin + location.pathname).toBe(
      "https://biaice.local:8443/realms/biaice/protocol/openid-connect/auth",
    );
    expect(location.searchParams.get("code_challenge_method")).toBe("S256");
    expect(location.searchParams.get("client_id")).toBe("biaice-web");

    const transactionCookie = response.cookies.get(AUTH_COOKIE_NAMES.transaction)?.value;
    const transaction = decodeLoginTransaction(transactionCookie);
    expect(transaction?.returnTo).toBe("/projects");
    expect(location.searchParams.get("state")).toBe(transaction?.state);
    expect(location.searchParams.get("nonce")).toBe(transaction?.nonce);
    expect(location.searchParams.get("code_challenge")).toBe(
      createCodeChallenge(transaction?.codeVerifier ?? ""),
    );

    const setCookie = response.headers.get("set-cookie") ?? "";
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie).toContain("SameSite=lax");
    expect(setCookie).toContain("Secure");
  });

  it("rejects a callback whose state does not match and consumes the transaction", async () => {
    const transaction: LoginTransaction = {
      version: 1,
      state: "state-".padEnd(43, "x"),
      nonce: "nonce-".padEnd(43, "x"),
      codeVerifier: "verifier-".padEnd(64, "x"),
      returnTo: "/projects",
      createdAt: Math.floor(Date.now() / 1000),
    };
    const providerFetch = vi.fn();
    vi.stubGlobal("fetch", providerFetch);
    const response = await completeLogin(
      configuredRequest("/api/auth/callback?code=authorization-code&state=wrong-state", {
        headers: {
          Cookie: cookieHeader({
            [AUTH_COOKIE_NAMES.transaction]: encodeLoginTransaction(transaction),
          }),
        },
      }),
    );

    expect(response.status).toBe(400);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    expect(await response.json()).toMatchObject({ code: "OIDC_STATE_INVALID", status: 400 });
    expect(response.headers.get("set-cookie")).toContain(
      `${AUTH_COOKIE_NAMES.transaction}=`,
    );
    expect(providerFetch).not.toHaveBeenCalled();
  });

  it("exchanges a valid code, verifies nonce and signature, and stores only HttpOnly tokens", async () => {
    const transaction: LoginTransaction = {
      version: 1,
      state: "state-".padEnd(43, "x"),
      nonce: "nonce-".padEnd(43, "x"),
      codeVerifier: "verifier-".padEnd(64, "x"),
      returnTo: "/projects/project-a",
      createdAt: Math.floor(Date.now() / 1000),
    };
    const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
    const keyId = "test-key";
    const now = Math.floor(Date.now() / 1000);
    const encode = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
    const header = encode({ alg: "RS256", kid: keyId, typ: "JWT" });
    const payload = encode({
      sub: "00000000-0000-4000-8000-000000000001",
      iss: REQUIRED_ENVIRONMENT.BIAICE_OIDC_ISSUER,
      aud: "biaice-web",
      exp: now + 3600,
      iat: now,
      nonce: transaction.nonce,
    });
    const idToken = `${header}.${payload}.${sign(
      "RSA-SHA256",
      Buffer.from(`${header}.${payload}`),
      privateKey,
    ).toString("base64url")}`;
    const accessToken = fakeAccessToken(now + 3600);
    const jwk = publicKey.export({ format: "jwk" });
    const providerFetch = vi.fn(async (input: URL | RequestInfo) => {
      if (String(input).endsWith("/protocol/openid-connect/token")) {
        return Response.json({
          access_token: accessToken,
          refresh_token: "refresh-token",
          id_token: idToken,
          token_type: "Bearer",
          expires_in: 3600,
          refresh_expires_in: 7200,
        });
      }
      return Response.json({
        keys: [{ ...jwk, kid: keyId, alg: "RS256", use: "sig" }],
      });
    });
    vi.stubGlobal("fetch", providerFetch);

    const response = await completeLogin(
      configuredRequest(`/api/auth/callback?code=valid-code&state=${transaction.state}`, {
        headers: {
          Cookie: cookieHeader({
            [AUTH_COOKIE_NAMES.transaction]: encodeLoginTransaction(transaction),
          }),
        },
      }),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "https://biaice.local:8443/projects/project-a",
    );
    expect(response.cookies.get(AUTH_COOKIE_NAMES.accessToken)?.value).toBe(accessToken);
    expect(response.cookies.get(AUTH_COOKIE_NAMES.refreshToken)?.value).toBe("refresh-token");
    expect(response.cookies.get(AUTH_COOKIE_NAMES.idToken)?.value).toBe(idToken);
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(providerFetch).toHaveBeenCalledTimes(2);
  });

  it("returns an RFC 7807 401 when the API proxy has no session", async () => {
    const upstreamFetch = vi.fn();
    vi.stubGlobal("fetch", upstreamFetch);
    const response = await proxyApiRequest(configuredRequest("/api/v1/me"), {
      params: Promise.resolve({ path: ["me"] }),
    });

    expect(response.status).toBe(401);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    expect(await response.json()).toMatchObject({ code: "AUTH_REQUIRED", status: 401 });
    expect(upstreamFetch).not.toHaveBeenCalled();
  });

  it("returns an RFC 7807 503 instead of inventing a session when configuration is absent", () => {
    delete process.env.BIAICE_OIDC_INTERNAL_ISSUER;
    const response = beginLogin(configuredRequest("/api/auth/login"));

    expect(response.status).toBe(503);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
  });

  it("rejects a cross-site write before reading or proxying its body", async () => {
    const upstreamFetch = vi.fn();
    vi.stubGlobal("fetch", upstreamFetch);
    const response = await proxyApiRequest(
      configuredRequest("/api/v1/projects", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Origin: "https://evil.example",
          "Sec-Fetch-Site": "cross-site",
        },
        body: JSON.stringify({ should_not_be_read: true }),
      }),
      { params: Promise.resolve({ path: ["projects"] }) },
    );

    expect(response.status).toBe(403);
    expect(await response.json()).toMatchObject({
      code: "CROSS_SITE_REQUEST_FORBIDDEN",
      status: 403,
    });
    expect(upstreamFetch).not.toHaveBeenCalled();
  });

  it("accepts an exact-origin logout when Fetch Metadata is unavailable", async () => {
    const providerFetch = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", providerFetch);
    const response = await logout(
      configuredRequest("/api/auth/logout", {
        method: "POST",
        headers: {
          Origin: REQUIRED_ENVIRONMENT.BIAICE_PUBLIC_ORIGIN,
          Cookie: cookieHeader({
            [AUTH_COOKIE_NAMES.accessToken]: "access-token",
            [AUTH_COOKIE_NAMES.refreshToken]: "refresh-token",
          }),
        },
      }),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      `${REQUIRED_ENVIRONMENT.BIAICE_PUBLIC_ORIGIN}/login`,
    );
    expect(response.cookies.get(AUTH_COOKIE_NAMES.accessToken)?.value).toBe("");
    expect(response.cookies.get(AUTH_COOKIE_NAMES.refreshToken)?.value).toBe("");
    expect(providerFetch).toHaveBeenCalledTimes(1);
  });

  it("strips caller identity and scope headers before injecting the session bearer", async () => {
    const accessToken = fakeAccessToken(Math.floor(Date.now() / 1000) + 3600);
    const upstreamFetch = vi.fn(
      async (_input: URL | RequestInfo, _init?: RequestInit) => {
        void _input;
        void _init;
        return new Response("streamed", {
          status: 200,
          headers: { "Content-Type": "text/plain" },
        });
      },
    );
    vi.stubGlobal("fetch", upstreamFetch);
    const response = await proxyApiRequest(
      configuredRequest("/api/v1/projects?cursor=next", {
        headers: {
          Authorization: "Bearer caller-controlled",
          Cookie: cookieHeader({
            [AUTH_COOKIE_NAMES.accessToken]: accessToken,
            unrelated: "must-not-forward",
          }),
          "X-Tenant-ID": "caller-controlled",
          "X-Project-Scope": "caller-controlled",
        },
      }),
      { params: Promise.resolve({ path: ["projects"] }) },
    );

    expect(response.status).toBe(200);
    expect(await response.text()).toBe("streamed");
    expect(upstreamFetch).toHaveBeenCalledOnce();
    const [url, init] = upstreamFetch.mock.calls[0] ?? [];
    expect(String(url)).toBe("http://api:8000/api/v1/projects?cursor=next");
    const headers = new Headers(init?.headers);
    expect(headers.get("authorization")).toBe(`Bearer ${accessToken}`);
    expect(headers.has("cookie")).toBe(false);
    expect(headers.has("x-tenant-id")).toBe(false);
    expect(headers.has("x-project-scope")).toBe(false);
  });

  it("refreshes a near-expiry access token before forwarding", async () => {
    const now = Math.floor(Date.now() / 1000);
    const oldAccessToken = fakeAccessToken(now + 10);
    const newAccessToken = fakeAccessToken(now + 3600);
    const providerFetch = vi.fn(async (input: URL | RequestInfo, _init?: RequestInit) => {
      void _init;
      if (String(input).endsWith("/protocol/openid-connect/token")) {
        return Response.json({
          access_token: newAccessToken,
          refresh_token: "rotated-refresh-token",
          token_type: "Bearer",
          expires_in: 3600,
          refresh_expires_in: 7200,
        });
      }
      return new Response("ok", { status: 200 });
    });
    vi.stubGlobal("fetch", providerFetch);
    const response = await proxyApiRequest(
      configuredRequest("/api/v1/me", {
        headers: {
          Cookie: cookieHeader({
            [AUTH_COOKIE_NAMES.accessToken]: oldAccessToken,
            [AUTH_COOKIE_NAMES.refreshToken]: "current-refresh-token",
          }),
        },
      }),
      { params: Promise.resolve({ path: ["me"] }) },
    );

    expect(response.status).toBe(200);
    expect(providerFetch).toHaveBeenCalledTimes(2);
    const secondCallHeaders = new Headers(providerFetch.mock.calls[1]?.[1]?.headers);
    expect(secondCallHeaders.get("authorization")).toBe(`Bearer ${newAccessToken}`);
    expect(response.headers.get("set-cookie")).toContain(AUTH_COOKIE_NAMES.accessToken);
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });
});
