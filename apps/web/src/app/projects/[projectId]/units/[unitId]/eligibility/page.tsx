import type { Metadata } from "next";
import { EligibilityMount } from "@/features/simulation/public";

export const metadata: Metadata = {
  title: "推荐资格",
};

type EligibilityPageProps = {
  readonly params: Promise<{ projectId: string; unitId: string }>;
};

export default async function EligibilityPage({ params }: EligibilityPageProps) {
  const { unitId } = await params;
  return <EligibilityMount unitId={unitId} />;
}
