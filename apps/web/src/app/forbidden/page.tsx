import type { Metadata } from "next";
import { PageFrame } from "@/components/shell";
import { Card, LinkButton, Notice } from "@/components/ui";

export const metadata: Metadata = {
  title: "访问被拒绝",
};

export default function ForbiddenPage() {
  return (
    <PageFrame
      description="当前身份缺少执行该操作所需的租户、数据域、项目或决策单元权限。"
      eyebrow="403 · FORBIDDEN"
      narrow
      title="访问被拒绝"
    >
      <Card>
        <Notice title="授权事实以服务端为准" tone="danger">
          前端不会通过隐藏按钮替代后端鉴权，也不会说明受限对象是否存在。
        </Notice>
        <div style={{ marginTop: "1rem" }}>
          <LinkButton href="/projects">返回已授权项目</LinkButton>
        </div>
      </Card>
    </PageFrame>
  );
}
