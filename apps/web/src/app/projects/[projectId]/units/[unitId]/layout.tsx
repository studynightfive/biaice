import type { ReactNode } from "react";
import { AppShell } from "@/components/shell";

type UnitLayoutProps = {
  children: ReactNode;
  params: Promise<{
    projectId: string;
    unitId: string;
  }>;
};

export default async function UnitLayout({ children, params }: UnitLayoutProps) {
  const { projectId, unitId } = await params;

  return (
    <AppShell projectId={projectId} unitId={unitId}>
      {children}
    </AppShell>
  );
}
