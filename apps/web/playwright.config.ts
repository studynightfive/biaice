import { defineConfig, devices } from "@playwright/test";

const isCi = Boolean(process.env.CI);
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL?.trim();
const chromiumExecutablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?.trim();
const localBaseUrl = "http://127.0.0.1:3000";
const chromiumLaunchOptions = chromiumExecutablePath
  ? { launchOptions: { executablePath: chromiumExecutablePath } }
  : {};

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: isCi,
  retries: isCi ? 2 : 0,
  workers: isCi ? 2 : undefined,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  reporter: isCi
    ? [["line"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : "line",
  use: {
    baseURL: externalBaseUrl || localBaseUrl,
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], ...chromiumLaunchOptions },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"], ...chromiumLaunchOptions },
    },
  ],
  webServer: externalBaseUrl
    ? undefined
    : {
        command: "npm run dev",
        url: `${localBaseUrl}/api/health`,
        env: {
          NEXT_TELEMETRY_DISABLED: "1",
        },
        reuseExistingServer: !isCi,
        timeout: 180_000,
      },
});
