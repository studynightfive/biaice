import { NextResponse, type NextRequest } from "next/server";
import { BffConfigurationError, readBffConfig } from "@/server/auth/config";
import {
  clearSessionCookies,
  setTransactionCookie,
} from "@/server/auth/cookies";
import { configurationProblem } from "@/server/auth/problem";
import {
  createCodeChallenge,
  createCodeVerifier,
  encodeLoginTransaction,
  normalizeReturnTo,
  randomOpaqueValue,
  type LoginTransaction,
} from "@/server/auth/security";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET(request: NextRequest): NextResponse {
  let config;
  try {
    config = readBffConfig();
  } catch (error) {
    if (error instanceof BffConfigurationError) return configurationProblem(request);
    throw error;
  }

  const codeVerifier = createCodeVerifier();
  const transaction: LoginTransaction = {
    version: 1,
    state: randomOpaqueValue(),
    nonce: randomOpaqueValue(),
    codeVerifier,
    returnTo: normalizeReturnTo(request.nextUrl.searchParams.get("return_to")),
    createdAt: Math.floor(Date.now() / 1000),
  };
  const authorizationUrl = new URL(config.authorizationEndpoint);
  authorizationUrl.search = new URLSearchParams({
    response_type: "code",
    response_mode: "query",
    client_id: config.clientId,
    redirect_uri: config.callbackUrl,
    scope: "openid profile email",
    state: transaction.state,
    nonce: transaction.nonce,
    code_challenge: createCodeChallenge(codeVerifier),
    code_challenge_method: "S256",
  }).toString();

  const response = NextResponse.redirect(authorizationUrl, 307);
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("Pragma", "no-cache");
  response.headers.set("Referrer-Policy", "no-referrer");
  clearSessionCookies(response, config);
  setTransactionCookie(response, config, encodeLoginTransaction(transaction));
  return response;
}
