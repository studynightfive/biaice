import { NextResponse, type NextRequest } from "next/server";
import { BffConfigurationError, readBffConfig, type BffConfig } from "@/server/auth/config";
import {
  clearSessionCookies,
  clearTransactionCookie,
  setSessionCookies,
} from "@/server/auth/cookies";
import { configurationProblem, problemResponse } from "@/server/auth/problem";
import {
  AUTH_COOKIE_NAMES,
  decodeLoginTransaction,
  IdTokenValidationError,
  stateMatches,
} from "@/server/auth/security";
import { exchangeAuthorizationCode, OidcProviderError } from "@/server/auth/tokens";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function callbackProblem(
  request: NextRequest,
  config: BffConfig,
  status: number,
  code: string,
  title: string,
  detail: string,
): NextResponse {
  const response = problemResponse(request, status, code, title, detail);
  clearTransactionCookie(response, config);
  clearSessionCookies(response, config);
  return response;
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  let config: BffConfig;
  try {
    config = readBffConfig();
  } catch (error) {
    if (error instanceof BffConfigurationError) return configurationProblem(request);
    throw error;
  }

  const transaction = decodeLoginTransaction(
    request.cookies.get(AUTH_COOKIE_NAMES.transaction)?.value,
  );
  const suppliedState = request.nextUrl.searchParams.get("state");
  if (!transaction || !stateMatches(transaction.state, suppliedState)) {
    return callbackProblem(
      request,
      config,
      400,
      "OIDC_STATE_INVALID",
      "Invalid login response",
      "The login transaction is missing, expired, or does not match this browser.",
    );
  }

  if (request.nextUrl.searchParams.has("error")) {
    return callbackProblem(
      request,
      config,
      401,
      "OIDC_LOGIN_REJECTED",
      "Login rejected",
      "The local identity provider did not complete authentication.",
    );
  }
  const code = request.nextUrl.searchParams.get("code");
  if (!code) {
    return callbackProblem(
      request,
      config,
      400,
      "OIDC_CODE_MISSING",
      "Invalid login response",
      "The authorization response does not contain a code.",
    );
  }

  try {
    const tokens = await exchangeAuthorizationCode(
      config,
      code,
      transaction.codeVerifier,
      transaction.nonce,
    );
    const destination = new URL(transaction.returnTo, config.publicOrigin);
    const response = NextResponse.redirect(destination, 303);
    response.headers.set("Cache-Control", "no-store");
    response.headers.set("Pragma", "no-cache");
    response.headers.set("Referrer-Policy", "no-referrer");
    clearTransactionCookie(response, config);
    setSessionCookies(response, config, tokens);
    return response;
  } catch (error) {
    const providerResponseInvalid =
      error instanceof OidcProviderError || error instanceof IdTokenValidationError;
    return callbackProblem(
      request,
      config,
      providerResponseInvalid ? 502 : 500,
      providerResponseInvalid ? "OIDC_TOKEN_EXCHANGE_FAILED" : "INTERNAL_ERROR",
      providerResponseInvalid ? "Login could not be completed" : "Internal error",
      providerResponseInvalid
        ? "The local identity provider returned an unavailable or invalid token response."
        : "The login callback failed closed.",
    );
  }
}
