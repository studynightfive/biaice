import { type NextRequest, NextResponse } from "next/server";
import type { BffConfig } from "./config";
import { AUTH_COOKIE_NAMES, TRANSACTION_MAX_AGE_SECONDS } from "./security";
import type { TokenSet } from "./tokens";

const SESSION_COOKIE_PATH = "/api";
const AUTH_COOKIE_PATH = "/api/auth";

function cookieOptions(config: BffConfig, path: string, maxAge: number) {
  return {
    httpOnly: true,
    secure: config.secureCookies,
    sameSite: "lax" as const,
    path,
    maxAge: Math.max(0, Math.floor(maxAge)),
    priority: "high" as const,
  };
}

export function setTransactionCookie(
  response: NextResponse,
  config: BffConfig,
  value: string,
): void {
  response.cookies.set(
    AUTH_COOKIE_NAMES.transaction,
    value,
    cookieOptions(config, AUTH_COOKIE_PATH, TRANSACTION_MAX_AGE_SECONDS),
  );
}

export function clearTransactionCookie(response: NextResponse, config: BffConfig): void {
  response.cookies.set(
    AUTH_COOKIE_NAMES.transaction,
    "",
    cookieOptions(config, AUTH_COOKIE_PATH, 0),
  );
}

export function clearSessionCookies(response: NextResponse, config: BffConfig): void {
  response.cookies.set(
    AUTH_COOKIE_NAMES.accessToken,
    "",
    cookieOptions(config, SESSION_COOKIE_PATH, 0),
  );
  response.cookies.set(
    AUTH_COOKIE_NAMES.refreshToken,
    "",
    cookieOptions(config, SESSION_COOKIE_PATH, 0),
  );
  response.cookies.set(
    AUTH_COOKIE_NAMES.idToken,
    "",
    cookieOptions(config, AUTH_COOKIE_PATH, 0),
  );
}

export type CurrentSessionCookies = Readonly<{
  accessToken?: string;
  refreshToken?: string;
  idToken?: string;
}>;

export function readSessionCookies(request: NextRequest): CurrentSessionCookies {
  return {
    accessToken: request.cookies.get(AUTH_COOKIE_NAMES.accessToken)?.value,
    refreshToken: request.cookies.get(AUTH_COOKIE_NAMES.refreshToken)?.value,
    idToken: request.cookies.get(AUTH_COOKIE_NAMES.idToken)?.value,
  };
}

export function setSessionCookies(
  response: NextResponse,
  config: BffConfig,
  tokens: TokenSet,
  current: CurrentSessionCookies = {},
): void {
  response.cookies.set(
    AUTH_COOKIE_NAMES.accessToken,
    tokens.accessToken,
    cookieOptions(config, SESSION_COOKIE_PATH, tokens.accessMaxAge),
  );

  const refreshToken = tokens.refreshToken ?? current.refreshToken;
  if (refreshToken) {
    response.cookies.set(
      AUTH_COOKIE_NAMES.refreshToken,
      refreshToken,
      cookieOptions(config, SESSION_COOKIE_PATH, tokens.refreshMaxAge),
    );
  }

  const idToken = tokens.idToken ?? current.idToken;
  if (idToken) {
    response.cookies.set(
      AUTH_COOKIE_NAMES.idToken,
      idToken,
      cookieOptions(config, AUTH_COOKIE_PATH, tokens.idMaxAge),
    );
  }
}
