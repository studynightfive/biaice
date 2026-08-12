import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "标策 AI｜资料驱动的多智能体投标策略",
  description: "解析招标文件、本公司材料和竞争者历史投标信息，预测报价与评分区间，并生成稳妥中标、利润最大、均衡及利润保护方案。模拟结果不构成中标保证。",
  openGraph: {
    title: "标策 AI｜资料驱动的多智能体投标策略",
    description: "三类资料自动画像，四个目标方案同步推演。",
    type: "website",
    locale: "zh_CN",
    images: [
      {
        url: "https://bid-agent-lab-20260806.breezy-toad-2233.chatgpt.site/bid-strategy-social.png",
        width: 1536,
        height: 1024,
        alt: "多智能体投标策略与规则决策示意图",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "标策 AI｜资料驱动的多智能体投标策略",
    description: "预测竞争者报价与评分区间，自动生成多个合规报价方案。",
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
