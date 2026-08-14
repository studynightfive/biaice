import type { Metadata } from "next";
import { AccessAuditMount } from "@/features/access-audit/public";

export const metadata: Metadata = {
  title: "访问、审计与处置",
};

export default function AccessAuditPage() {
  return <AccessAuditMount />;
}
