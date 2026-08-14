import type { Metadata } from "next";
import { DocumentsMount } from "@/features/documents/public";

export const metadata: Metadata = {
  title: "资料摄入",
};

export default function DocumentsPage() {
  return <DocumentsMount />;
}
