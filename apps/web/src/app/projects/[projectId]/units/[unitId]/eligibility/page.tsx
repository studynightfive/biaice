import type { Metadata } from "next";
import { EligibilityMount } from "@/features/simulation/public";

export const metadata: Metadata = {
  title: "推荐资格",
};

export default function EligibilityPage() {
  return <EligibilityMount />;
}
