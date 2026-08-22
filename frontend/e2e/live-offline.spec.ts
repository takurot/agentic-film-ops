import { expect, test } from "@playwright/test";

test("Live backend failure stays failed and Retry starts a fresh attempt", async ({ page }) => {
  let requests = 0;
  let failRuntime = true;
  await page.route("https://api.example.test/api/runtime", async (route) => {
    requests += 1;
    if (failRuntime) { failRuntime = false; await route.abort("connectionrefused"); return; }
    await route.fulfill({ json: { mode: "LIVE_GEMINI", reasoning_provider: "google-genai", model: "gemini-test", mcp_transport: "stdio", adk_enabled: false } });
  });
  await page.route("https://api.example.test/api/production/health", (route) => route.fulfill({ json: {
    production_day_current: 1, production_day_total: 2, schedule_adherence_percent: 100,
    budget_spent_usd: 1, budget_total_usd: 2, scenes_completed: 1, scenes_total: 2,
    overall_risk: "LOW", total_scenes: 2, active_incidents: 0, today_scenes: [],
  } }));
  await page.route("https://api.example.test/api/incidents/active", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  await expect(page.getByText("BACKEND_UNAVAILABLE", { exact: true })).toBeVisible();
  await expect(page.getByText(/No sample results were substituted/i)).toBeVisible();
  await expect(page.getByText(/RECORDED REPLAY/i)).toHaveCount(0);
  await expect(page.getByText(/Production Day 27/i)).toHaveCount(0);
  const firstAttemptRequests = requests;
  expect(firstAttemptRequests).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText("LIVE GEMINI + MCP STDIO", { exact: true })).toBeVisible();
  await expect(page.getByText(/RECORDED REPLAY/i)).toHaveCount(0);
  expect(requests).toBeGreaterThan(firstAttemptRequests);
});

test("Live frontend rejects a non-Live backend runtime", async ({ page }) => {
  let nonRuntimeRequests = 0;
  await page.route("https://api.example.test/api/runtime", (route) => route.fulfill({
    json: { mode: "RECORDED_REPLAY", reasoning_provider: "recorded-fixture", model: null, mcp_transport: "stdio", adk_enabled: false },
  }));
  await page.route("https://api.example.test/api/production/health", (route) => { nonRuntimeRequests += 1; return route.abort(); });
  await page.route("https://api.example.test/api/incidents/active", (route) => { nonRuntimeRequests += 1; return route.abort(); });
  await page.goto("/");
  await expect(page.getByText("RUNTIME_MISMATCH", { exact: true })).toBeVisible();
  await expect(page.getByText(/RECORDED REPLAY/i)).toHaveCount(0);
  expect(nonRuntimeRequests).toBe(0);
});
