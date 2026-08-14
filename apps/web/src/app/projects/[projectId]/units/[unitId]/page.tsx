import { redirect } from "next/navigation";
import { buildUnitPath } from "@/lib/navigation/unit-routes";

type UnitIndexPageProps = {
  params: Promise<{
    projectId: string;
    unitId: string;
  }>;
};

export default async function UnitIndexPage({ params }: UnitIndexPageProps) {
  const { projectId, unitId } = await params;
  redirect(buildUnitPath(projectId, unitId, "/overview"));
}
