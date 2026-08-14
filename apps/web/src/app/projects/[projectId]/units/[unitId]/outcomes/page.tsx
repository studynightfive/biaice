import type { Metadata } from "next";
import { OutcomesMount } from "@/features/reports/public";

export const metadata: Metadata = {
  title: "结果与复盘",
};

export default function OutcomesPage() {
  return <OutcomesMount />;
}
