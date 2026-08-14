import type { Metadata } from "next";
import { SimulationMount } from "@/features/simulation/public";

export const metadata: Metadata = {
  title: "仿真与方案",
};

export default function SimulationPage() {
  return <SimulationMount />;
}
