import type { Metadata } from "next";
import { ApprovalsMount } from "@/features/approvals/public";

export const metadata: Metadata = {
  title: "审批中心",
};

export default function ApprovalsPage() {
  return <ApprovalsMount />;
}
