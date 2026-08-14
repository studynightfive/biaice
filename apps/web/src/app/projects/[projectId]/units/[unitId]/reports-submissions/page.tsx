import type { Metadata } from "next";
import { ReportsSubmissionsMount } from "@/features/reports/public";

export const metadata: Metadata = {
  title: "报告与提交",
};

export default function ReportsSubmissionsPage() {
  return <ReportsSubmissionsMount />;
}
