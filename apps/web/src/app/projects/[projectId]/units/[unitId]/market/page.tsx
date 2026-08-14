import type { Metadata } from "next";
import { MarketMount } from "@/features/market/public";

export const metadata: Metadata = {
  title: "竞对与市场",
};

export default function MarketPage() {
  return <MarketMount />;
}
