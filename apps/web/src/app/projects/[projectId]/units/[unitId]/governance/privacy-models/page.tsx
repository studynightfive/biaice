import type { Metadata } from "next";
import { PrivacyModelsMount } from "@/features/privacy-models/public";

export const metadata: Metadata = {
  title: "隐私与模型治理",
};

export default function PrivacyModelsPage() {
  return <PrivacyModelsMount />;
}
