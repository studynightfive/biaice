import type { Metadata } from "next";
import { EvidencePrecheckMount } from "@/features/evidence/public";

export const metadata: Metadata = {
  title: "证据、响应与预审",
};

export default function EvidencePrecheckPage() {
  return <EvidencePrecheckMount />;
}
