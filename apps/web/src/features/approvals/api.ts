/** Contract-aligned browser data layer for member-7 approvals and reports. */

import { getBiaiceClient, type BiaiceClient } from "@/lib/api/client";
import type {
  CreateRiskAcceptanceRequest,
  MeResponse,
  RevokeRiskAcceptanceRequest,
  RiskAcceptance,
} from "@biaice/contracts";

const NO_STORE: RequestCache = "no-store";
const NEXT_REVALIDATE = { revalidate: 0 } as const;

function apiClient(): BiaiceClient {
  return getBiaiceClient();
}

function readOnly() {
  return { cache: NO_STORE, next: NEXT_REVALIDATE };
}

function writeOptions(action: string, hint: string, idempotencyKey?: string) {
  return {
    cache: NO_STORE,
    next: NEXT_REVALIDATE,
    idempotencyKey: idempotencyKey ?? newIdempotencyKey(action, hint),
  };
}

function segment(value: string): string {
  return encodeURIComponent(value);
}

export function newIdempotencyKey(action: string, hint?: string): string {
  const suffix = hint ? `:${hint}` : "";
  return `${action}:${globalThis.crypto.randomUUID()}${suffix}`;
}

export function getCurrentIdentity(): Promise<MeResponse> {
  return apiClient().request<MeResponse>("GET", "/api/v1/me", readOnly());
}

export async function listRiskAcceptances(unitId: string): Promise<RiskAcceptance[]> {
  const response = await apiClient().request<{ readonly items: ReadonlyArray<RiskAcceptance> }>(
    "GET",
    `/api/v1/decision-units/${segment(unitId)}/risk-acceptances`,
    readOnly(),
  );
  return [...response.items];
}

export function createRiskAcceptance(
  unitId: string,
  body: CreateRiskAcceptanceRequest,
  idempotencyKey?: string,
): Promise<RiskAcceptance> {
  return apiClient().request<RiskAcceptance>(
    "POST",
    `/api/v1/decision-units/${segment(unitId)}/risk-acceptances`,
    {
      ...writeOptions("create_risk_acceptance", unitId, idempotencyKey),
      body,
    },
  );
}

export function revokeRiskAcceptance(
  riskAcceptanceId: string,
  body: RevokeRiskAcceptanceRequest,
  idempotencyKey?: string,
): Promise<RiskAcceptance> {
  return apiClient().request<RiskAcceptance>(
    "POST",
    `/api/v1/risk-acceptances/${segment(riskAcceptanceId)}/revoke`,
    {
      ...writeOptions("revoke_risk_acceptance", riskAcceptanceId, idempotencyKey),
      body,
    },
  );
}

