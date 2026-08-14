import { NextResponse, type NextRequest } from "next/server";
import { BffConfigurationError, readBffConfig } from "@/server/auth/config";
import {
  clearSessionCookies,
  clearTransactionCookie,
  readSessionCookies,
} from "@/server/auth/cookies";
import { configurationProblem, problemResponse } from "@/server/auth/problem";
import { isSameOriginMutation } from "@/server/auth/security";
import { revokeSession } from "@/server/auth/tokens";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<NextResponse> {
  let config;
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
      "Logout requires the configured same-origin browser context.",
    );
  }

  const current = readSessionCookies(request);
  await revokeSession(config, current.refreshToken);
  const response = NextResponse.redirect(`${config.publicOrigin}/login`, 303);
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("Clear-Site-Data", '"cache"');
  clearTransactionCookie(response, config);
  clearSessionCookies(response, config);
  return response;
}
