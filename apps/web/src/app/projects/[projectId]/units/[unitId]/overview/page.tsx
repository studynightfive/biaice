import type { Metadata } from "next";
import { UnitOverviewMount } from "@/features/projects/public";

export const metadata: Metadata = {
  title: "决策单元概览",
};

export default function UnitOverviewPage() {
  return <UnitOverviewMount />;
}
