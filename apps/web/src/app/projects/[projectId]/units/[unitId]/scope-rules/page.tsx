import type { Metadata } from "next";
import { ScopeRulesMount } from "@/features/rules/public";

export const metadata: Metadata = {
  title: "制度、范围与规则",
};

export default function ScopeRulesPage() {
  return <ScopeRulesMount />;
}
