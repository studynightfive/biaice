import type { Metadata } from "next";
import { BaselineScenariosMount } from "@/features/simulation/public";

export const metadata: Metadata = {
  title: "决策基线与场景",
};

export default function BaselineScenariosPage() {
  return <BaselineScenariosMount />;
}
