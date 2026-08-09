import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "标策 AI｜合规优先的多智能体投标决策",
  description: "按项目招标文件执行资格、符合性、详细评分与利润约束，通过多智能体竞演寻找可解释的投标策略。模拟结果不构成中标保证。",
  openGraph: {
    title: "标策 AI｜多智能体投标决策",
    description: "先过门，再竞分；先守利，再优化报价。",
    type: "website",
    locale: "zh_CN",
    images: [
      {
        url: "https://bid-agent-lab-20260806.breezy-toad-2233.chatgpt.site/bid-strategy-social.png",
        width: 1536,
        height: 1024,
        alt: "四个投标策略路径经过规则审查后汇入决策结果",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "标策 AI｜多智能体投标决策",
    description: "先过门，再竞分；先守利，再优化报价。",
    images: ["https://bid-agent-lab-20260806.breezy-toad-2233.chatgpt.site/bid-strategy-social.png"],
  },
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
