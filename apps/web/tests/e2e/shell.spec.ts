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

test("shell pages have no serious or critical axe violations", async ({ page }) => {
  await page.goto("/projects/demo-project/units/demo-unit/overview");

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    violation.impact === "serious" || violation.impact === "critical",
  );

  expect(blockingViolations).toEqual([]);
});
