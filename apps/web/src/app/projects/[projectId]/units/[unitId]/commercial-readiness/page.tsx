import type { Metadata } from "next";
import { CommercialReadinessMount } from "@/features/commercial/public";

export const metadata: Metadata = {
  title: "商业政策与就绪",
};

export default function CommercialReadinessPage() {
  return <CommercialReadinessMount />;
}
