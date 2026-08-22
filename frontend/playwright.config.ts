import { defineConfig, devices } from "@playwright/test";
import { E2E_BASE_URL, LOCAL_E2E_BASE_URL, USE_LOCAL_E2E_SERVER } from "./e2e/runtime";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: E2E_BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: USE_LOCAL_E2E_SERVER ? {
    command: "npm run serve:export",
    url: LOCAL_E2E_BASE_URL,
    reuseExistingServer: false,
    timeout: 30_000,
  } : undefined,
});
