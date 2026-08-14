import { PageFrame } from "@/components/shell";
import { Card, StatusBadge } from "@/components/ui";

export default function LoadingPage() {
  return (
    <PageFrame
      description="正在从当前 URL 与服务端状态恢复页面上下文。"
      eyebrow="LOADING"
      narrow
      title="正在准备工作区"
    >
      <Card aria-live="polite" aria-busy="true">
        <StatusBadge tone="info">加载中</StatusBadge>
      </Card>
    </PageFrame>
  );
}
