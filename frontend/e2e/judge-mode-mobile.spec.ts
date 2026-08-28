import { test, expect } from "@playwright/test";

const VIEWPORTS = [
  { name: "Mobile (iPhone 13)", width: 390, height: 844 },
  { name: "Tablet (iPad Gen 7)", width: 768, height: 1024 },
  { name: "Desktop (1440x900)", width: 1440, height: 900 },
];

for (const vp of VIEWPORTS) {
  test.describe(`Judge Mode & Mobile End-to-End [${vp.name}]`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("completes full judge evaluation flow with 0 horizontal overflow and no CTA obscuration", async ({
      page,
    }) => {
      const consoleErrors: string[] = [];
      const pageErrors: Error[] = [];
      const failedRequests: string[] = [];

      page.on("console", (msg) => {
        if (msg.type() === "error") {
          consoleErrors.push(msg.text());
        }
      });
      page.on("pageerror", (err) => {
        pageErrors.push(err);
      });
      page.on("requestfailed", (req) => {
        failedRequests.push(`${req.method()} ${req.url()} — ${req.failure()?.errorText}`);
      });

      await page.goto("/");

      // 1. Initial State: Verify Judge Executive Summary & First Viewport Metrics
      await expect(page.getByRole("region", { name: /Judge Executive Summary/i })).toBeVisible();
      await expect(page.getByText(/\+\$79,800 Net Saved/i)).toBeVisible();
      await expect(page.getByText(/Scene 42 Outdoor Rain Alert/i)).toBeVisible();

      // Check Zero Horizontal Overflow on Initial State
      const initialOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth
      );
      expect(
        initialOverflow,
        `Document has horizontal overflow at ${vp.width}x${vp.height} initial state`
      ).toBe(false);

      // 2. Trigger Analysis CTA
      const startBtn = page.getByRole("button", {
        name: /Play Recorded Analysis|Start AI Impact Analysis/i,
      });
      await expect(startBtn).toBeVisible();
      // Ensure button is clickable and not covered by overlay
      await startBtn.click();

      // 3. Option Comparison & Approval State
      const optionA = page.getByText(/Option A:/i).first();
      await expect(optionA).toBeVisible({ timeout: 10_000 });

      // Check Zero Horizontal Overflow during Analysis & Options
      const midOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth
      );
      expect(
        midOverflow,
        `Document has horizontal overflow at ${vp.width}x${vp.height} options state`
      ).toBe(false);

      // 4. Click Approve Plan
      const approveBtn = page.getByRole("button", { name: /APPROVE PLAN/i }).first();
      await expect(approveBtn).toBeVisible();
      await approveBtn.click();

      // 5. Resolution & Before/After Summary
      const resolvedSummary = page.getByTestId("before-after-summary");
      await expect(resolvedSummary).toBeVisible({ timeout: 10_000 });
      await expect(page.getByRole("heading", { name: /INCIDENT RESOLVED/i })).toBeVisible();
      await expect(page.getByText(/\+\$4,200/i).first()).toBeVisible();


      // Check Zero Horizontal Overflow on Completed State
      const finalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth
      );
      expect(
        finalOverflow,
        `Document has horizontal overflow at ${vp.width}x${vp.height} final state`
      ).toBe(false);

      // 6. Test 1-Click Evidence Deep-Links
      const mcpEvidenceBtn = page.getByRole("button", { name: /§15.1 MCP Stdio Calls/i });
      await expect(mcpEvidenceBtn).toBeVisible();
      await mcpEvidenceBtn.click();

      // 7. Verify zero errors throughout the test
      expect(consoleErrors).toEqual([]);
      expect(pageErrors).toEqual([]);
      expect(failedRequests).toEqual([]);
    });
  });
}
