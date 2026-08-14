import { PageFrame } from "@/components/shell";
import { Card, LinkButton, Notice } from "@/components/ui";

export default function NotFoundPage() {
  return (
    <PageFrame
      description="该页面不存在，或当前会话无权确认其是否存在。系统不会在错误页面泄露项目、单元或资料信息。"
      eyebrow="404 · NOT FOUND"
      narrow
      title="未找到可访问的内容"
    >
      <Card>
        <Notice title="请从已授权入口重新进入" tone="warning">
          检查项目和决策单元上下文，或联系租户管理员确认你的访问范围。
        </Notice>
        <div style={{ marginTop: "1rem" }}>
          <LinkButton href="/projects">返回项目列表</LinkButton>
        </div>
      </Card>
    </PageFrame>
  );
}
