import type { BffConfig } from "./config";
import { readJwtExpiration, verifyIdToken } from "./security";

const TOKEN_REQUEST_TIMEOUT_MS = 10_000;
const DEFAULT_REFRESH_MAX_AGE_SECONDS = 8 * 60 * 60;
const MAX_COOKIE_AGE_SECONDS = 7 * 24 * 60 * 60;

export type TokenSet = Readonly<{
  accessToken: string;
  refreshToken?: string;
  idToken?: string;
  accessMaxAge: number;
  refreshMaxAge: number;
  idMaxAge: number;
}>;

type TokenEndpointPayload = {
  access_token?: unknown;
  refresh_token?: unknown;
  id_token?: unknown;
  expires_in?: unknown;
  refresh_expires_in?: unknown;
  token_type?: unknown;
};

export class OidcProviderError extends Error {
  constructor() {
    super("The local identity provider did not complete the token request");
    this.name = "OidcProviderError";
  }
}

function positiveSeconds(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return fallback;
  return Math.min(Math.floor(value), MAX_COOKIE_AGE_SECONDS);
}

function accessLifetime(accessToken: string, declaredLifetime: unknown): number {
  const now = Math.floor(Date.now() / 1000);
  const expiration = readJwtExpiration(accessToken);
  const jwtLifetime = expiration ? expiration - now : Number.POSITIVE_INFINITY;
  const responseLifetime = positiveSeconds(declaredLifetime, 5 * 60);
  return Math.max(1, Math.min(jwtLifetime, responseLifetime, MAX_COOKIE_AGE_SECONDS));
}

async function requestTokens(config: BffConfig, form: URLSearchParams): Promise<TokenEndpointPayload> {
  let response: Response;
  try {
    response = await fetch(config.tokenEndpoint, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: form,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(TOKEN_REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw new OidcProviderError();
  }
  if (!response.ok) throw new OidcProviderError();
  try {
    return (await response.json()) as TokenEndpointPayload;
  } catch {
    throw new OidcProviderError();
  }
}

async function validateTokenPayload(
  config: BffConfig,
  payload: TokenEndpointPayload,
  expectedNonce?: string,
  requireIdToken = false,
): Promise<TokenSet> {
  if (
    typeof payload.access_token !== "string" ||
    !payload.access_token ||
    (payload.token_type !== undefined &&
      (typeof payload.token_type !== "string" || payload.token_type.toLowerCase() !== "bearer"))
  ) {
    throw new OidcProviderError();
  }
  const accessExpiration = readJwtExpiration(payload.access_token);
  if (accessExpiration !== null && accessExpiration <= Math.floor(Date.now() / 1000)) {
    throw new OidcProviderError();
  }
  if (requireIdToken && (typeof payload.id_token !== "string" || !payload.id_token)) {
    throw new OidcProviderError();
  }
  if (typeof payload.id_token === "string" && payload.id_token) {
    await verifyIdToken(payload.id_token, config, expectedNonce);
  }

  const accessMaxAge = accessLifetime(payload.access_token, payload.expires_in);
  return {
    accessToken: payload.access_token,
    refreshToken:
      typeof payload.refresh_token === "string" && payload.refresh_token
        ? payload.refresh_token
        : undefined,
    idToken: typeof payload.id_token === "string" && payload.id_token ? payload.id_token : undefined,
    accessMaxAge,
    refreshMaxAge: positiveSeconds(
      payload.refresh_expires_in,
      DEFAULT_REFRESH_MAX_AGE_SECONDS,
    ),
    idMaxAge: accessMaxAge,
  };
}

export async function exchangeAuthorizationCode(
  config: BffConfig,
  code: string,
  codeVerifier: string,
  expectedNonce: string,
): Promise<TokenSet> {
  const payload = await requestTokens(
    config,
    new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.clientId,
      code,
      code_verifier: codeVerifier,
      redirect_uri: config.callbackUrl,
    }),
  );
  return validateTokenPayload(config, payload, expectedNonce, true);
}

export async function refreshAccessToken(
  config: BffConfig,
  refreshToken: string,
): Promise<TokenSet> {
  const payload = await requestTokens(
    config,
    new URLSearchParams({
      grant_type: "refresh_token",
      client_id: config.clientId,
      refresh_token: refreshToken,
    }),
  );
  return validateTokenPayload(config, payload);
}

export async function revokeSession(
  config: BffConfig,
  refreshToken: string | undefined,
): Promise<void> {
  if (!refreshToken) return;
  try {
    await fetch(config.logoutEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: config.clientId,
        refresh_token: refreshToken,
      }),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(TOKEN_REQUEST_TIMEOUT_MS),
    });
  } catch {
    // Local cookies are still cleared. Logout must not disclose provider failures or keep a browser session.
  }
}
