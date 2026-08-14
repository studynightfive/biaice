import {
  createHash,
  createHmac,
  createPublicKey,
  type JsonWebKey as NodeJsonWebKey,
  randomBytes,
  timingSafeEqual,
  verify as verifySignature,
} from "node:crypto";
import type { NextRequest } from "next/server";
import type { BffConfig } from "./config";

export const AUTH_COOKIE_NAMES = Object.freeze({
  transaction: "biaice_oidc_transaction",
  accessToken: "biaice_access_token",
  refreshToken: "biaice_refresh_token",
  idToken: "biaice_id_token",
});

export const TRANSACTION_MAX_AGE_SECONDS = 10 * 60;
export const ACCESS_REFRESH_WINDOW_SECONDS = 60;

export type LoginTransaction = Readonly<{
  version: 1;
  state: string;
  nonce: string;
  codeVerifier: string;
  returnTo: string;
  createdAt: number;
}>;

type GlobalWithTransactionKey = typeof globalThis & {
  [key: symbol]: Buffer | undefined;
};

const TRANSACTION_KEY_SYMBOL = Symbol.for("biaice.auth.transaction-cookie-key.v1");

function transactionSigningKey(): Buffer {
  const sharedGlobal = globalThis as GlobalWithTransactionKey;
  const existing = sharedGlobal[TRANSACTION_KEY_SYMBOL];
  if (existing) {
    return existing;
  }
  const key = randomBytes(32);
  sharedGlobal[TRANSACTION_KEY_SYMBOL] = key;
  return key;
}

function base64UrlEncode(value: Buffer | string): string {
  return Buffer.from(value).toString("base64url");
}

function decodeJsonSegment<T>(segment: string): T {
  return JSON.parse(Buffer.from(segment, "base64url").toString("utf8")) as T;
}

function constantTimeTextEqual(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left);
  const rightBytes = Buffer.from(right);
  return leftBytes.length === rightBytes.length && timingSafeEqual(leftBytes, rightBytes);
}

function transactionSignature(payload: string): string {
  return createHmac("sha256", transactionSigningKey()).update(payload).digest("base64url");
}

export function randomOpaqueValue(byteLength = 32): string {
  return randomBytes(byteLength).toString("base64url");
}

export function createCodeVerifier(): string {
  return randomOpaqueValue(64);
}

export function createCodeChallenge(codeVerifier: string): string {
  return createHash("sha256").update(codeVerifier).digest("base64url");
}

export function normalizeReturnTo(value: string | null | undefined): string {
  const fallback = "/projects";
  if (
    !value ||
    value.length > 2048 ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    /[\\\u0000-\u001f\u007f]/.test(value)
  ) {
    return fallback;
  }

  let decoded = value;
  try {
    for (let pass = 0; pass < 2; pass += 1) {
      const next = decodeURIComponent(decoded);
      if (next === decoded) break;
      decoded = next;
    }
  } catch {
    return fallback;
  }
  if (
    decoded.startsWith("//") ||
    decoded.includes("\\") ||
    /[\u0000-\u001f\u007f]/.test(decoded)
  ) {
    return fallback;
  }

  const localBase = "https://return-to.invalid";
  const parsed = new URL(value, localBase);
  if (parsed.origin !== localBase) {
    return fallback;
  }
  return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

export function encodeLoginTransaction(transaction: LoginTransaction): string {
  const payload = base64UrlEncode(JSON.stringify(transaction));
  return `${payload}.${transactionSignature(payload)}`;
}

export function decodeLoginTransaction(
  cookieValue: string | undefined,
  nowSeconds = Math.floor(Date.now() / 1000),
): LoginTransaction | null {
  if (!cookieValue) return null;
  const segments = cookieValue.split(".");
  if (segments.length !== 2) return null;
  const [payload, suppliedSignature] = segments;
  if (!payload || !suppliedSignature) return null;
  if (!constantTimeTextEqual(transactionSignature(payload), suppliedSignature)) return null;

  try {
    const value = decodeJsonSegment<Partial<LoginTransaction>>(payload);
    if (
      value.version !== 1 ||
      typeof value.state !== "string" ||
      typeof value.nonce !== "string" ||
      typeof value.codeVerifier !== "string" ||
      typeof value.returnTo !== "string" ||
      typeof value.createdAt !== "number" ||
      value.state.length < 32 ||
      value.nonce.length < 32 ||
      value.codeVerifier.length < 43 ||
      normalizeReturnTo(value.returnTo) !== value.returnTo ||
      value.createdAt > nowSeconds + 30 ||
      nowSeconds - value.createdAt > TRANSACTION_MAX_AGE_SECONDS
    ) {
      return null;
    }
    return value as LoginTransaction;
  } catch {
    return null;
  }
}

export function stateMatches(expected: string, supplied: string | null): boolean {
  return supplied !== null && constantTimeTextEqual(expected, supplied);
}

export function readJwtExpiration(token: string | undefined): number | null {
  if (!token) return null;
  const segments = token.split(".");
  if (segments.length !== 3 || !segments[1]) return null;
  try {
    const payload = decodeJsonSegment<{ exp?: unknown }>(segments[1]);
    return typeof payload.exp === "number" && Number.isFinite(payload.exp) ? payload.exp : null;
  } catch {
    return null;
  }
}

type OidcJsonWebKey = NodeJsonWebKey & {
  kid?: string;
  alg?: string;
  use?: string;
};
type JsonWebKeySet = { keys?: OidcJsonWebKey[] };
type IdTokenClaims = {
  sub?: unknown;
  iss?: unknown;
  aud?: unknown;
  azp?: unknown;
  exp?: unknown;
  iat?: unknown;
  nonce?: unknown;
};

export class IdTokenValidationError extends Error {
  constructor() {
    super("The identity provider returned an invalid ID token");
    this.name = "IdTokenValidationError";
  }
}

export async function verifyIdToken(
  token: string,
  config: BffConfig,
  expectedNonce?: string,
): Promise<void> {
  const segments = token.split(".");
  if (segments.length !== 3 || segments.some((segment) => !segment)) {
    throw new IdTokenValidationError();
  }

  try {
    const header = decodeJsonSegment<{ alg?: unknown; kid?: unknown }>(segments[0]);
    const claims = decodeJsonSegment<IdTokenClaims>(segments[1]);
    if (header.alg !== "RS256" || typeof header.kid !== "string") {
      throw new IdTokenValidationError();
    }

    const jwksResponse = await fetch(config.jwksEndpoint, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
    if (!jwksResponse.ok) throw new IdTokenValidationError();
    const jwks = (await jwksResponse.json()) as JsonWebKeySet;
    const jwk = jwks.keys?.find(
      (candidate) =>
        candidate.kid === header.kid &&
        candidate.kty === "RSA" &&
        (!candidate.alg || candidate.alg === "RS256") &&
        (!candidate.use || candidate.use === "sig"),
    );
    if (!jwk) throw new IdTokenValidationError();

    const publicKey = createPublicKey({ key: jwk, format: "jwk" });
    const signatureValid = verifySignature(
      "RSA-SHA256",
      Buffer.from(`${segments[0]}.${segments[1]}`),
      publicKey,
      Buffer.from(segments[2], "base64url"),
    );
    if (!signatureValid) throw new IdTokenValidationError();

    const now = Math.floor(Date.now() / 1000);
    const audiences =
      typeof claims.aud === "string"
        ? [claims.aud]
        : Array.isArray(claims.aud) && claims.aud.every((value) => typeof value === "string")
          ? claims.aud
          : [];
    if (
      claims.iss !== config.publicIssuer ||
      typeof claims.sub !== "string" ||
      !claims.sub ||
      !audiences.includes(config.clientId) ||
      (audiences.length > 1 && claims.azp !== config.clientId) ||
      typeof claims.exp !== "number" ||
      claims.exp <= now - 30 ||
      typeof claims.iat !== "number" ||
      claims.iat > now + 60 ||
      (expectedNonce !== undefined &&
        (typeof claims.nonce !== "string" || !constantTimeTextEqual(expectedNonce, claims.nonce)))
    ) {
      throw new IdTokenValidationError();
    }
  } catch (error) {
    if (error instanceof IdTokenValidationError) throw error;
    throw new IdTokenValidationError();
  }
}

export function isSameOriginMutation(request: NextRequest, config: BffConfig): boolean {
  if (request.method === "GET" || request.method === "HEAD") return true;
  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  // Origin is the authoritative CSRF boundary. Fetch Metadata is a useful
  // additional signal, but some Chromium automation, WebViews and proxies omit
  // it; reject an explicitly non-same-origin value without requiring presence.
  if (!origin || (fetchSite !== null && fetchSite !== "same-origin")) return false;
  try {
    return new URL(origin).origin === config.publicOrigin;
  } catch {
    return false;
  }
}
