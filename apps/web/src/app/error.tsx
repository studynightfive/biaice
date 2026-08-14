"use client";

import { PageFrame } from "@/components/shell";
import { Button, Card, Notice } from "@/components/ui";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <PageFrame
      description="页面未能安全完成请求。错误详情不会在浏览器界面回显敏感载荷。"
      eyebrow="REQUEST FAILED"
      narrow
      title="暂时无法完成操作"
    >
      <Card>
        <Notice title="状态未被标记为成功" tone="danger">
          请重试；如果问题持续存在，请使用服务端 request_id 联系管理员排查。
        </Notice>
        <div style={{ marginTop: "1rem" }}>
          <Button onClick={reset}>重试当前页面</Button>
        </div>
      </Card>
    </PageFrame>
  );
}
