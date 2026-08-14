import type { Metadata } from "next";
import { PageFrame } from "@/components/shell";
import { Button, Card, Notice, StatusBadge } from "@/components/ui";
import styles from "./login.module.css";

export const metadata: Metadata = {
  title: "登录",
};

export default function LoginPage() {
  return (
    <PageFrame
      description="使用组内本地 Keycloak 身份进入。浏览器不会在本页面收集或保存账户密码。"
      eyebrow="LOCAL IDENTITY · OIDC + PKCE"
      narrow
      title="进入标策 AI"
    >
      <div className={styles.grid}>
        <Card eyebrow="SIGN IN" title="本地身份登录">
          <div className={styles.stack}>
            <StatusBadge tone="info">Keycloak OIDC</StatusBadge>
            <form action="/api/auth/login" className={styles.loginForm} method="get">
              <input name="return_to" type="hidden" value="/projects" />
              <p>继续后将跳转到局域网内的统一身份服务，并在完成 MFA 后返回经过校验的本地路径。</p>
              <Button type="submit">使用本地身份系统继续</Button>
            </form>
            <Notice title="没有站内密码表单" tone="warning">
              首次改密、MFA 与会话管理均由本地身份系统完成；局域网环境不等同于可信身份。
            </Notice>
          </div>
        </Card>
        <Card eyebrow="SECURITY" title="登录前确认">
          <ul className={styles.securityList}>
            <li>访问地址应为组内统一的 biaice.local。</li>
            <li>浏览器应信任组长分发的本地 CA。</li>
            <li>不要绕过证书警告或共享测试账户。</li>
          </ul>
        </Card>
      </div>
    </PageFrame>
  );
}
