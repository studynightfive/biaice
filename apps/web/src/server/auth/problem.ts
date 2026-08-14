import { randomUUID } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";

const SAFE_REQUEST_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/;

export function problemResponse(
  request: NextRequest,
  status: number,
  code: string,
  title: string,
  detail: string,
): NextResponse {
  const suppliedRequestId = request.headers.get("x-request-id");
  const requestId =
    suppliedRequestId && SAFE_REQUEST_ID.test(suppliedRequestId)
      ? suppliedRequestId
      : randomUUID();
  const response = new NextResponse(
    JSON.stringify({
      type: `urn:biaice:problem:${code.toLowerCase().replaceAll("_", "-")}`,
      title,
      status,
      detail,
      code,
      request_id: requestId,
    }),
    {
      status,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": "application/problem+json",
        Pragma: "no-cache",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Request-ID": requestId,
      },
    },
  );
  return response;
}

export function configurationProblem(request: NextRequest): NextResponse {
  return problemResponse(
    request,
    503,
    "AUTH_NOT_CONFIGURED",
    "Authentication unavailable",
    "The local identity BFF is not configured. Ask the platform operator to verify its runtime settings.",
  );
}
