import type { Metadata } from "next";
import { ApprovalsMount } from "@/features/approvals/public";

export const metadata: Metadata = {
  title: "审批与风险接受",
};

export default function ApprovalsPage() {
  return <ApprovalsMount />;
}
