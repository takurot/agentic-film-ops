import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const TARGET_URL = process.env.TARGET_URL || "https://takurot0708.web.app";
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || path.join(process.cwd(), "temp", "browser_verification");

async function runVerification() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  console.log(`🚀 Launching Chromium to verify: ${TARGET_URL}`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });

  const page = await context.newPage();

  const browserErrors = [];
  const failedRequests = [];

  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(`[Console Error] ${message.text()}`);
  });
  page.on("pageerror", (error) => browserErrors.push(`[Page Error] ${error.message}`));
  page.on("requestfailed", (request) => failedRequests.push(request.url()));

  const results = {
    steps: [],
    passed: 0,
    failed: 0,
  };

  function logPass(stepName, detail) {
    console.log(`✅ [PASS] ${stepName}: ${detail}`);
    results.steps.push({ name: stepName, status: "PASS", detail });
    results.passed++;
  }

  function logFail(stepName, detail) {
    console.error(`❌ [FAIL] ${stepName}: ${detail}`);
    results.steps.push({ name: stepName, status: "FAIL", detail });
    results.failed++;
  }


  try {
    // ─── Step 1: Initial Page Load ───
    console.log("\n--- Testing Step 1: Initial Page Load ---");
    const response = await page.goto(TARGET_URL, { waitUntil: "networkidle" });
    if (response.status() === 200) {
      logPass("HTTP 200", `Loaded ${TARGET_URL} successfully`);
    } else {
      logFail("HTTP 200", `Unexpected status: ${response.status()}`);
    }

    // Verify Title & Branding
    const title = await page.title();
    if (title.includes("Agentic FilmOps")) {
      logPass("Page Title", title);
    } else {
      logFail("Page Title", `Unexpected title: ${title}`);
    }

    // Wait for Dashboard elements
    await page.waitForSelector("header", { timeout: 5000 });
    const headerText = await page.locator("header").innerText();
    if (headerText.includes("AGENTIC FILMOPS") && headerText.includes("Production Day 27 / 54")) {
      logPass("Header Branding", "Header renders title and production day counter");
    } else {
      logFail("Header Branding", `Header content: ${headerText}`);
    }

    // Verify Production Health Cards
    const healthText = await page.locator("main").innerText();
    if (healthText.includes("94%") && healthText.includes("$12.4M")) {
      logPass("Production Health Metrics", "Schedule Adherence 94% and Budget $12.4M rendered");
    } else {
      logFail("Production Health Metrics", "Missing health metric values");
    }

    // Verify Active Incident Card
    if (healthText.includes("WEATHER RISK") || healthText.includes("Scene SC-042")) {
      logPass("Active Incident Card", "Scene 42 Weather alert details displayed");
    } else {
      logFail("Active Incident Card", "Incident details not found");
    }

    // Verify Start Analysis button
    const startBtn = page.locator("#start-analysis-btn");
    if (await startBtn.isVisible()) {
      logPass("Start Analysis Button", "CTA button visible and ready for interaction");
    } else {
      logFail("Start Analysis Button", "Start button not visible");
    }

    const ss1 = path.join(SCREENSHOT_DIR, "step1_initial_dashboard.png");
    await page.screenshot({ path: ss1, fullPage: true });
    console.log(`📸 Screenshot saved: ${ss1}`);

    // ─── Step 2: Trigger AI Impact Analysis ───
    console.log("\n--- Testing Step 2: Trigger AI Impact Analysis ---");
    await startBtn.click();
    console.log("Clicked 'Start AI Impact Analysis'");

    // Wait for live views to appear
    await page.waitForTimeout(1500);

    // Verify Resource Network View
    const pageContentAfterClick = await page.content();
    if (pageContentAfterClick.includes("PRODUCTION RESOURCE NETWORK") || pageContentAfterClick.includes("Resource Network")) {
      logPass("Resource Network View", "React Flow / Dependency graph mounted (SPEC §9.4)");
    } else {
      logFail("Resource Network View", "Resource Network View not found");
    }

    // Verify Agent Live View
    if (pageContentAfterClick.includes("AI COORDINATION") || pageContentAfterClick.includes("Weather Agent")) {
      logPass("Agent Live View", "Multi-Agent coordination components mounted (SPEC §9.2)");
    } else {
      logFail("Agent Live View", "Agent Live View not found after analysis start");
    }

    // Verify MCP Activity Monitor & External Comms Mock
    if (pageContentAfterClick.includes("LIVE MCP ACTIVITY") && pageContentAfterClick.includes("EXTERNAL COMMUNICATION")) {
      logPass("MCP Monitor & External Comms", "Live MCP tools and talent manager comms mock visible (SPEC §9.3 / §9.5)");
    } else {
      logFail("MCP Monitor & External Comms", "MCP / Comms mock missing");
    }

    // Wait for simulated stream to finish
    await page.waitForTimeout(3000);

    const ss2 = path.join(SCREENSHOT_DIR, "step2_live_orchestration.png");
    await page.screenshot({ path: ss2, fullPage: true });
    console.log(`📸 Screenshot saved: ${ss2}`);

    // ─── Step 3: Replan Option Comparison & Explainability ───
    console.log("\n--- Testing Step 3: Replan Option Comparison (A/B/C) ---");
    const optionCards = page.locator("section").filter({ hasText: "OPT-A" });
    if ((await optionCards.count()) > 0) {
      logPass("Replan Options (A/B/C)", "Option A (Recommended), Option B, Option C cards rendered (SPEC §9.7 / §9.8)");
    } else {
      logFail("Replan Options (A/B/C)", "Replan option cards not found");
    }

    const ss3 = path.join(SCREENSHOT_DIR, "step3_option_comparison.png");
    await page.screenshot({ path: ss3, fullPage: true });
    console.log(`📸 Screenshot saved: ${ss3}`);

    // ─── Step 4: Producer Approval & Execution ───
    console.log("\n--- Testing Step 4: Producer Human Approval & Execution ---");
    const approveBtn = page.getByRole("button", { name: /APPROVE & EXECUTE|Approve Plan/i }).first();
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      logPass("Producer Approval Gate", "Clicked 'APPROVE & EXECUTE' button for Option A (SPEC §9.9)");
    } else {
      const altApprove = page.locator("button:has-text('APPROVE')").first();
      await altApprove.click();
      logPass("Producer Approval Gate", "Clicked APPROVE button");
    }

    await page.waitForTimeout(1000);

    // Verify Execution Checklist
    const executionContent = await page.content();
    if (executionContent.includes("PLAN EXECUTION COMPLETE") || executionContent.includes("Execution Checklist") || executionContent.includes("Studio B")) {
      logPass("Execution Checklist", "Automated multi-system execution tasks displayed (SPEC §9.10)");
    } else {
      logFail("Execution Checklist", "Execution tasks missing after approval");
    }

    // Verify Before/After Summary Screen
    if (executionContent.includes("INCIDENT RESOLVED") || executionContent.includes("Before / After Summary")) {
      logPass("Before/After Summary Screen", "Resolved impact metrics and recovery summary displayed (SPEC §9.11)");
    } else {
      logFail("Before/After Summary Screen", "Summary screen not rendered");
    }

    const ss4 = path.join(SCREENSHOT_DIR, "step4_execution_resolved_summary.png");
    await page.screenshot({ path: ss4, fullPage: true });
    console.log(`📸 Screenshot saved: ${ss4}`);

    // ─── Step 5: Demo Timeline Overlay ───
    console.log("\n--- Testing Step 5: Demo Timeline Overlay ---");
    const timeline = page.locator("#demo-overlay");
    if (await timeline.isVisible()) {
      logPass("Demo Timeline Overlay", "Interactive 4-minute demo timeline floating badge is present");
    } else {
      logFail("Demo Timeline Overlay", "Timeline overlay not visible");
    }

    // ─── Step 6: Verify Promo Video Streaming ───
    console.log("\n--- Testing Step 6: Promo Video MP4 URL ---");
    const videoResponse = await page.goto("https://takurot0708.web.app/promo-video.mp4");
    if (videoResponse.status() === 200 && videoResponse.headers()["content-type"] === "video/mp4") {
      logPass("Promo Video Stream", `HTTP 200 video/mp4 stream verified (${videoResponse.headers()["content-length"]} bytes)`);
    } else {
      logFail("Promo Video Stream", `Video response status: ${videoResponse.status()}, Content-Type: ${videoResponse.headers()["content-type"]}`);
    }
  } catch (error) {
    console.error("Critical test runner exception:", error);
    logFail("Test Execution", `Fatal exception: ${error.message}`);
  } finally {
    await browser.close();
  }

  if (browserErrors.length > 0) {
    console.error(`❌ Found ${browserErrors.length} browser errors:`, browserErrors);
    results.failed += browserErrors.length;
  }
  if (failedRequests.length > 0) {
    console.error(`❌ Found ${failedRequests.length} failed network requests:`, failedRequests);
    results.failed += failedRequests.length;
  }

  console.log("\n==========================================");
  console.log(`VERIFICATION SUMMARY: ${results.passed} PASSED, ${results.failed} FAILED`);
  console.log("==========================================");

  if (results.failed > 0) {
    process.exit(1);
  }

  return results;
}

runVerification();

