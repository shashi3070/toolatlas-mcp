import { chromium } from "@playwright/test";
import { strict as assert } from "node:assert";

const BASE = "http://localhost:8081";

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Test 1: Rapid navigation between pages
// ---------------------------------------------------------------------------
async function testRapidNavigation(page) {
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "warning" && msg.text().includes("unmounted")) errors.push(msg.text());
  });

  const pages = ["/", "/tools", "/servers", "/proxies", "/analytics", "/glossary", "/graph"];
  for (const path of pages) {
    await page.goto(`${BASE}${path}`, { waitUntil: "commit" });
    await delay(50);
  }

  await delay(500);

  assert.equal(errors.length, 0, `Errors/warnings during rapid nav: ${errors.join("\n")}`);
  console.log("  PASS");
}

// ---------------------------------------------------------------------------
// Test 2: Navigate away mid-request (intercept and delay API)
// ---------------------------------------------------------------------------
async function testNavigateAwayMidRequest(page) {
  await page.route("**/api/tools**", async (route) => {
    await delay(5000);
    await route.continue();
  });

  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "warning" && msg.text().includes("unmounted")) errors.push(msg.text());
  });

  await page.goto(`${BASE}/tools`, { waitUntil: "commit" });
  await delay(200);
  await page.goto(`${BASE}/servers`, { waitUntil: "networkidle" });
  await delay(500);

  const unexpected = errors.filter(
    (e) => !e.includes("CanceledError") && !e.includes("canceled") && !e.includes("aborted") && !e.includes("ERR_CANCELED") && !e.includes("unmounted"),
  );
  assert.equal(unexpected.length, 0, `Unexpected errors: ${unexpected.join(", ")}`);
  console.log("  PASS (only abort/cancel errors)");
}

// ---------------------------------------------------------------------------
// Test 3: Rapid tab switching in Graph page
// ---------------------------------------------------------------------------
async function testGraphTabSwitching(page) {
  await page.route("**/api/graph/**", async (route) => {
    await delay(3000);
    await route.continue();
  });

  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto(`${BASE}/graph`, { waitUntil: "networkidle" });

  const buttons = page.locator("button", { hasText: /Call Flow|Relationships|Topology/ });
  const count = await buttons.count();
  for (let i = 0; i < count; i++) {
    await buttons.nth(i).click();
    await delay(100);
  }

  await delay(500);

  const unexpected = errors.filter(
    (e) => !e.includes("CanceledError") && !e.includes("canceled") && !e.includes("aborted") && !e.includes("ERR_CANCELED"),
  );
  assert.equal(unexpected.length, 0, `Unexpected errors: ${unexpected.join(", ")}`);
  console.log("  PASS");
}

// ---------------------------------------------------------------------------
// Test 4: Navigate to proxy detail, then away immediately
// ---------------------------------------------------------------------------
async function testProxyDetailNavigation(page) {
  await page.route("**/api/proxies/**", async (route) => {
    await delay(3000);
    await route.continue();
  });

  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto(`${BASE}/proxies`, { waitUntil: "commit" });
  await delay(200);

  const link = page.locator("a", { hasText: "Configure" }).first();
  if (await link.isVisible()) {
    await link.click();
  }
  await delay(200);
  await page.goto(`${BASE}/tools`, { waitUntil: "networkidle" });
  await delay(500);

  const unexpected = errors.filter(
    (e) => !e.includes("CanceledError") && !e.includes("canceled") && !e.includes("aborted") && !e.includes("ERR_CANCELED"),
  );
  assert.equal(unexpected.length, 0, `Unexpected errors: ${unexpected.join(", ")}`);
  console.log("  PASS");
}

// ---------------------------------------------------------------------------
// Test 5: Rapid tool edit dialog open/close while data loads
// ---------------------------------------------------------------------------
async function testToolEditDialog(page) {
  await page.route("**/api/glossary/**", async (route) => {
    await delay(3000);
    await route.continue();
  });

  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto(`${BASE}/tools`, { waitUntil: "networkidle" });

  // Click first edit pencil button
  const editBtn = page.locator("button", { has: page.locator("svg.lucide-pencil") }).first();
  if (await editBtn.isVisible()) {
    await editBtn.click();
    await delay(200);
    // Navigate away while dialog is open and glossary data is loading
    await page.goto(`${BASE}/servers`, { waitUntil: "networkidle" });
  }

  await delay(500);

  const unexpected = errors.filter(
    (e) => !e.includes("CanceledError") && !e.includes("canceled") && !e.includes("aborted") && !e.includes("ERR_CANCELED"),
  );
  assert.equal(unexpected.length, 0, `Unexpected errors: ${unexpected.join(", ")}`);
  console.log("  PASS");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log("Launching browser...");
  const headless = !process.env.HEADED;
  const browser = await chromium.launch({ headless });

  let passed = 0;
  let failed = 0;

  const tests = [
    ["Rapid navigation between pages", testRapidNavigation],
    ["Navigate away mid-API request", testNavigateAwayMidRequest],
    ["Graph tab switching with slow API", testGraphTabSwitching],
    ["Proxy detail navigation mid-load", testProxyDetailNavigation],
    ["Tool edit dialog while loading", testToolEditDialog],
  ];

  for (const [name, fn] of tests) {
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1280, height: 800 });
    try {
      console.log(`\nTest: ${name}`);
      await fn(page);
      passed++;
    } catch (err) {
      console.log(`  FAIL: ${err.message}`);
      failed++;
    } finally {
      await page.close();
    }
  }

  console.log(`\n${"=".repeat(50)}`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  await browser.close();
  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
