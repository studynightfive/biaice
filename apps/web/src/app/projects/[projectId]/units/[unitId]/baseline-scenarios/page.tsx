import type { Metadata } from "next";
import { BaselineScenariosMount } from "@/features/simulation/public";

export const metadata: Metadata = {
  title: "决策基线与场景",
};

type BaselineScenariosPageProps = {
  readonly params: Promise<{ projectId: string; unitId: string }>;
};

export default async function BaselineScenariosPage({ params }: BaselineScenariosPageProps) {
  const { unitId } = await params;
  return <BaselineScenariosMount unitId={unitId} />;
}
