import type { Metadata } from "next";
import type { ReactNode } from "react";
import { GlobalHeader, SiteFooter } from "@/components/shell";
import "./globals.css";

const publicOrigin = process.env.BIAICE_PUBLIC_ORIGIN ?? "https://biaice.local:8443";

export const metadata: Metadata = {
  metadataBase: new URL(publicOrigin),
  title: {
    default: "标策 AI｜可审计投标决策辅助",
    template: "%s｜标策 AI",
  },
  description:
    "本地自托管的投标决策辅助工作区，用于规则、证据、场景、审批与结果的可追溯协作；不保证中标。",
  applicationName: "标策 AI",
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    type: "website",
    locale: "zh_CN",
    title: "标策 AI｜可审计投标决策辅助",
    description: "规则、证据、场景与审批保持可追溯；仅用于企业内部决策参考。",
    images: [
      {
        url: "/bid-strategy-social.png",
        width: 1731,
        height: 909,
        alt: "标策 AI 规则、证据与策略决策示意",
      },
    ],
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <a className="skip-link" href="#main-content">
          跳到主要内容
        </a>
        <GlobalHeader />
        <div id="main-content" tabIndex={-1}>
          {children}
        </div>
        <SiteFooter />
      </body>
    </html>
  );
}
