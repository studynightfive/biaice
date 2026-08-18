import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("login delegates credentials to local OIDC", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByRole("heading", { level: 1, name: "进入标策 AI" })).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await expect(page.getByRole("button", { name: "使用本地身份系统继续" })).toBeVisible();
  const loginForm = page.locator('form[action="/api/auth/login"]');
  await expect(loginForm).toHaveAttribute("method", "get");
  await expect(loginForm.locator('input[name="return_to"]')).toHaveValue("/projects");
});

test("web health and auth handlers are mounted without requiring Keycloak", async ({ request }) => {
  const health = await request.get("/api/health");
  expect(health.status()).toBe(200);
  expect(await health.json()).toEqual({ service: "biaice-web", status: "ok" });

  const login = await request.get("/api/auth/login", { maxRedirects: 0 });
  expect([307, 503]).toContain(login.status());
  if (login.status() === 503) {
    expect(login.headers()["content-type"]).toContain("application/problem+json");
    expect(await login.json()).toMatchObject({
      code: "AUTH_NOT_CONFIGURED",
      status: 503,
    });
  } else {
    expect(login.headers().location).toContain("/protocol/openid-connect/auth");
  }
});

test("deep feature route restores the unit shell from the URL", async ({ page }) => {
  await page.goto("/projects/demo-project/units/demo-unit/governance/access-audit");

  await expect(page.getByRole("navigation", { name: "决策单元阶段导航" })).toBeVisible();
  await expect(page.getByText("demo-project / demo-unit")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "访问、审计与数据处置" })).toBeVisible();
});

test("simulation route forwards the URL unit through the same-origin BFF", async ({ page }) => {
  const requestedPaths: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    requestedPaths.push(path);
    const body = path === "/api/v1/me"
      ? { mfa_verified: true }
      : { items: [] };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.goto("/projects/demo-project/units/demo-unit/baseline-scenarios");

  await expect(page.getByRole("heading", { level: 1, name: "决策基线与场景" })).toBeVisible();
  await expect(page.getByText("尚无冻结基线")).toBeVisible();
  await expect.poll(() => requestedPaths).toContain(
    "/api/v1/decision-units/demo-unit/decision-baselines",
  );
});

test("member 5 writes are usable while BYOK remains fail-closed", async ({ page }) => {
  await page.goto("/projects/demo-project/units/demo-unit/market");
  await expect(page.getByRole("heading", { level: 1, name: "竞对与市场治理" })).toBeVisible();
  const createCompetitor = page.getByRole("button", { name: "创建竞对" });
  await expect(createCompetitor).toBeDisabled();
  await page.getByLabel("法定名称").fill("合成竞对甲");
  await expect(createCompetitor).toBeEnabled();

  await page.goto("/projects/demo-project/units/demo-unit/governance/privacy-models");
  await expect(page.getByRole("heading", { level: 1, name: "隐私与外部处理治理" })).toBeVisible();
  await expect(page.getByRole("button", { name: "创建处理活动记录" })).toBeEnabled();

  await page.goto("/settings/ai-providers");
  await expect(page.getByRole("heading", { level: 1, name: "AI 服务商配置" })).toBeVisible();
  await expect(page.getByText("BYOK BLOCKED")).toBeVisible();
  await page.getByLabel("配置 ID").fill("00000000-0000-4000-8000-000000000551");
  await expect(page.getByRole("button", { name: "写入新 Key" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "固定载荷连接测试" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "暂停配置" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "撤销配置" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "紧急撤销 Key" })).toBeEnabled();
});

test("shell pages have no serious or critical axe violations", async ({ page }) => {
  await page.goto("/projects/demo-project/units/demo-unit/overview");

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    violation.impact === "serious" || violation.impact === "critical",
  );

  expect(blockingViolations).toEqual([]);
});
