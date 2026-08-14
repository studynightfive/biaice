import type { Metadata } from "next";
import { PageFrame } from "@/components/shell";
import { Button, Card, LinkButton, Notice, StatusBadge } from "@/components/ui";
import styles from "./account.module.css";

export const metadata: Metadata = {
  title: "账户",
};

export default function AccountPage() {
  return (
    <PageFrame
      description="查看本地身份会话、租户与数据域范围。角色提示只改善使用体验，所有授权仍由服务端强制执行。"
      eyebrow="ACCOUNT · IDENTITY CONTEXT"
      narrow
      title="账户与访问范围"
    >
      <div className={styles.stack}>
        <Card eyebrow="SESSION" title="当前会话">
          <StatusBadge tone="warning">身份契约待接入</StatusBadge>
          <dl className={styles.details} style={{ marginTop: "1rem" }}>
            <dt>登录身份</dt>
            <dd>等待 IdentityContext</dd>
            <dt>租户 / 数据域</dt>
            <dd>等待 TenantScope</dd>
            <dt>MFA</dt>
            <dd>等待服务端会话声明</dd>
            <dt>授权范围</dt>
            <dd>等待 PermissionGuard 投影</dd>
          </dl>
        </Card>
        <Notice title="不在浏览器伪造身份" tone="info">
          页面不会从 localStorage、URL 参数或局域网地址推断角色、租户、MFA 或项目权限。
        </Notice>
        <div className={styles.actions}>
          <LinkButton href="/login" variant="secondary">
            前往登录页
          </LinkButton>
          <form action="/api/auth/logout" method="post">
            <Button type="submit" variant="secondary">
              退出本地会话
            </Button>
          </form>
        </div>
      </div>
    </PageFrame>
  );
}
