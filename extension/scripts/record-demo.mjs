// Captures the popup + page screenshots used to assemble docs/screenshots/demo.gif.
//
// Prerequisites (see docs/demo-script.md § Setup):
//   1. Backend running with PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true
//   2. `python demo/serve_demo.py` running on :8080
//   3. `npm run build` already run (this script copies dist/, it doesn't build it)
//
// Usage: node scripts/record-demo.mjs
// Output: PNG frames in a temp directory (path printed at the end). Compose
// them into the final GIF with a separate Pillow script — see
// docs/demo-gif-script.md for the compositing approach.
//
// Why this needs a patched, temporary copy of the extension (never the real
// dist/ or manifest.json): the real toolbar popup is not a tab, so
// `chrome.tabs.query({active:true, currentWindow:true})` inside Popup.tsx
// correctly resolves to the page the user is looking at. There is no way to
// click the real toolbar button from Playwright, so this script opens
// popup.html as a real tab/window instead — which makes that same query
// resolve to the popup's own tab. Three test-only adjustments compensate:
//   - "tabs" permission + an init script patches that one query shape to
//     return the real demo-page tab (fetched from the service worker before
//     the popup opens); every other chrome.* call passes through untouched.
//   - "web_accessible_resources" entry for popup.html, so it can be opened
//     via window.open() from a regular http(s) page.
//   - an extra host_permission for the demo server's origin, so
//     chrome.scripting.executeScript (the danger overlay injection) doesn't
//     depend on the activeTab gesture grant a real toolbar click would give.
// None of this ships; it only exists in the temp copy this script creates.
import { chromium } from "playwright";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXTENSION_ROOT = path.resolve(__dirname, "..");
const DIST_DIR = path.join(EXTENSION_ROOT, "dist");

const TMP_ROOT = path.join(os.tmpdir(), "phishlens-record-demo");
const EXT_PATH = path.join(TMP_ROOT, "ext");
const USER_DATA_DIR = path.join(TMP_ROOT, "profile");
const FRAMES_DIR = path.join(TMP_ROOT, "frames");

const DEMO_ORIGIN = "http://localhost:8080";
const SHOTS = [
  { name: "01-safe", url: `${DEMO_ORIGIN}/pages/safe.html` },
  { name: "02-suspicious", url: `${DEMO_ORIGIN}/pages/suspicious.html` },
  { name: "03-dangerous", url: `${DEMO_ORIGIN}/pages/phishlens-demo-dangerous-login-secure-update.html` },
];

function preparePatchedExtension() {
  if (!fs.existsSync(DIST_DIR)) {
    throw new Error(`${DIST_DIR} not found — run "npm run build" first.`);
  }
  fs.rmSync(EXT_PATH, { recursive: true, force: true });
  fs.cpSync(DIST_DIR, EXT_PATH, { recursive: true });

  const manifestPath = path.join(EXT_PATH, "manifest.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  manifest.permissions = Array.from(new Set([...manifest.permissions, "tabs"]));
  manifest.host_permissions = Array.from(new Set([...manifest.host_permissions, `${DEMO_ORIGIN}/*`]));
  manifest.web_accessible_resources = [
    { resources: ["src/popup/popup.html"], matches: ["http://*/*", "https://*/*"] },
  ];
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
}

// See the file-level comment: patches the one chrome.tabs.query() call shape
// Popup.tsx uses so it resolves to the real demo-page tab instead of the
// popup's own (simulated) tab.
function popupTabPatch(realTab) {
  const original = chrome.tabs.query.bind(chrome.tabs);
  chrome.tabs.query = function (queryInfo, callback) {
    if (queryInfo && queryInfo.active && queryInfo.currentWindow) {
      const result = [realTab];
      if (callback) {
        callback(result);
        return undefined;
      }
      return Promise.resolve(result);
    }
    return original(queryInfo, callback);
  };
}

async function getRealDemoTab(worker) {
  return worker.evaluate(async (origin) => {
    const tabs = await chrome.tabs.query({});
    const demoTab = tabs.find((tab) => tab.url && tab.url.startsWith(origin));
    if (!demoTab) throw new Error("demo tab not found");
    return demoTab;
  }, DEMO_ORIGIN);
}

async function waitForPopupReady(popupPage) {
  await popupPage.waitForFunction(
    () => {
      const status = document.querySelector(".risk-panel .status");
      return status && status.textContent && !status.textContent.includes("Checking");
    },
    { timeout: 20000 },
  );
  await popupPage.waitForTimeout(900);
}

async function openPopup(context, mainPage, extensionId, realTab) {
  await context.addInitScript(popupTabPatch, realTab);
  const popupPromise = context.waitForEvent("page");
  await mainPage.evaluate((extId) => {
    window.open(`chrome-extension://${extId}/src/popup/popup.html`, "phishlens-popup", "width=400,height=720");
  }, extensionId);
  const popupPage = await popupPromise;
  await popupPage.setViewportSize({ width: 380, height: 700 });
  return popupPage;
}

async function main() {
  preparePatchedExtension();
  fs.rmSync(USER_DATA_DIR, { recursive: true, force: true });
  fs.rmSync(FRAMES_DIR, { recursive: true, force: true });
  fs.mkdirSync(FRAMES_DIR, { recursive: true });

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    viewport: { width: 1100, height: 720 },
    args: [`--disable-extensions-except=${EXT_PATH}`, `--load-extension=${EXT_PATH}`],
  });

  let [main] = context.pages();
  if (!main) main = await context.newPage();

  let worker = context.serviceWorkers()[0];
  if (!worker) worker = await context.waitForEvent("serviceworker", { timeout: 15000 });
  const extensionId = worker.url().split("/")[2];
  console.log("Extension ID:", extensionId);

  for (const shot of SHOTS) {
    await main.bringToFront();
    await main.goto(shot.url, { waitUntil: "networkidle" });
    await main.waitForTimeout(500);

    const realTab = await getRealDemoTab(worker);
    const popup = await openPopup(context, main, extensionId, realTab);
    await waitForPopupReady(popup);

    // The very first /analyze call after launch is occasionally slow enough
    // (cold connection, not application logic) to miss the extension's
    // request timeout, leaving the popup in local-only mode. Clicking
    // Refresh reissues the request once the connection is warm.
    const backendActive = await popup
      .locator(".mode-banner")
      .innerText()
      .then((text) => !text.includes("unavailable") && !text.includes("not active"))
      .catch(() => false);
    if (!backendActive) {
      console.log(`  ${shot.name}: backend not active on first try, refreshing once...`);
      await popup.locator('button[aria-label="Refresh analysis"]').click();
      await waitForPopupReady(popup);
    }

    await popup.screenshot({ path: path.join(FRAMES_DIR, `${shot.name}-popup.png`) });

    if (shot.name === "03-dangerous") {
      await main.bringToFront();
      await main.waitForTimeout(1000);
      await main.screenshot({ path: path.join(FRAMES_DIR, `${shot.name}-overlay.png`) });
    } else {
      await main.bringToFront();
      await main.screenshot({ path: path.join(FRAMES_DIR, `${shot.name}-page.png`) });
    }

    await popup.close();
  }

  await context.close();
  console.log("Frames written to", FRAMES_DIR);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
