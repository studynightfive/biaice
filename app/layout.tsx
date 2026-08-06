import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "标策 AI｜多智能体投标决策台",
  description: "在利润约束下，通过多智能体竞演寻找更优投标报价的交互式演示。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
