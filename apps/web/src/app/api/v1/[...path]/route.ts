import type { NextRequest } from "next/server";
import { proxyApiRequest } from "@/server/auth/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type ApiRouteContext = {
  params: Promise<{ path: string[] }>;
};

export function GET(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}

export function HEAD(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}

export function POST(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}

export function PUT(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}

export function PATCH(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}

export function DELETE(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}

export function OPTIONS(request: NextRequest, context: ApiRouteContext) {
  return proxyApiRequest(request, context);
}
