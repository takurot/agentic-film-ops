import { expect, test } from "@playwright/test";
import { E2E_BASE_URL } from "./runtime";

test("Recorded Replay completes without backend, SSE, WebSocket, or browser errors", async ({ page }) => {
  const browserErrors: string[] = [];
  const failedRequests: string[] = [];
  const backendRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(request.url()));
  page.on("request", (request) => {
    const url = new URL(request.url());
    const isStaticOrigin = url.origin === new URL(E2E_BASE_URL).origin;
    if (!isStaticOrigin || url.pathname.startsWith("/api/")) backendRequests.push(request.url());
  });
  await page.addInitScript(() => {
    const counters = { fetch: 0, eventSource: 0, webSocket: 0 };
    Object.defineProperty(window, "__networkCounters", { value: counters });
    const originalFetch = window.fetch;
    window.fetch = ((...args: Parameters<typeof fetch>) => { counters.fetch += 1; return originalFetch(...args); }) as typeof fetch;
    const OriginalEventSource = window.EventSource;
    window.EventSource = class extends OriginalEventSource {
      constructor(url: string | URL, init?: EventSourceInit) { counters.eventSource += 1; super(url, init); }
    };
    const OriginalWebSocket = window.WebSocket;
    window.WebSocket = class extends OriginalWebSocket {
      constructor(url: string | URL, protocols?: string | string[]) { counters.webSocket += 1; super(url, protocols); }
    };
  });

  await page.goto("/");
  const banner = page.getByTestId("runtime-mode-banner");
  await expect(banner).toBeInViewport();
  await expect(banner).toContainText("RECORDED REPLAY / SAMPLE DATA");
  await page.getByRole("button", { name: "Play Recorded Analysis" }).click();
  await page.getByRole("button", { name: /Approve & Execute/i }).click();
  await expect(page.getByTestId("before-after-summary")).toContainText("RECORDED REPLAY / SAMPLE DATA");

  // Verify horizontal overflow (SPEC layout constraint)
  const hasHorizontalOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth;
  });
  expect(hasHorizontalOverflow).toBe(false);

  const counters = await page.evaluate(() => (window as typeof window & { __networkCounters: { fetch: number; eventSource: number; webSocket: number } }).__networkCounters);
  expect(counters).toEqual({ fetch: 0, eventSource: 0, webSocket: 0 });
  expect(backendRequests).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(browserErrors).toEqual([]);
});

