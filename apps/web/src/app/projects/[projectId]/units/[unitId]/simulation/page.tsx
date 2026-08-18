import type { Metadata } from "next";
import { SimulationMount } from "@/features/simulation/public";

export const metadata: Metadata = {
  title: "仿真与方案",
};

type SimulationPageProps = {
  readonly params: Promise<{ projectId: string; unitId: string }>;
};

export default async function SimulationPage({ params }: SimulationPageProps) {
  const { unitId } = await params;
  return <SimulationMount unitId={unitId} />;
}
