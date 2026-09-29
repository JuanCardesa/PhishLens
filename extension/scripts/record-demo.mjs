// Captures real popup + page screenshots from the built extension: the README
// screenshots and the source images for the Chrome Web Store screenshots
// (scripts/take-screenshots.mjs).
//
// Prerequisites (see docs/demo-script.md § Setup):
//   1. Backend running on :8000 with PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true
//   2. `python demo/serve_demo.py` running on :8080
//   3. `npm run build` already run (this script copies dist/, it doesn't build it)
//
// Usage: node scripts/record-demo.mjs [--docs]
// Output: PNG frames in a temp directory (path printed at the end).
// --docs also writes docs/screenshots/popup-{safe,suspicious,dangerous,local-only}.png
// and docs/screenshots/danger-overlay.png.
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

const DOCS_SCREENSHOTS_DIR = path.resolve(EXTENSION_ROOT, "..", "docs", "screenshots");
const WRITE_DOCS = process.argv.includes("--docs");

const DEMO_ORIGIN = "http://localhost:8080";
const SETTINGS_KEY = "phishlens:settings";
// Nothing listens on the discard port, so /analyze fails fast and the popup
// shows its real "Backend unavailable" fallback instead of a staged one.
const UNREACHABLE_BACKEND = "http://localhost:9";
const SHOTS = [
  { name: "01-safe", url: `${DEMO_ORIGIN}/pages/safe.html`, doc: "popup-safe.png" },
  { name: "02-suspicious", url: `${DEMO_ORIGIN}/pages/suspicious.html`, doc: "popup-suspicious.png" },
  {
    name: "03-dangerous",
    url: `${DEMO_ORIGIN}/pages/phishlens-demo-dangerous-login-secure-update.html`,
    doc: "popup-dangerous.png",
    overlayDoc: "danger-overlay.png",
  },
  { name: "04-local-only", url: `${DEMO_ORIGIN}/pages/safe.html`, doc: "popup-local-only.png", backendOff: true },
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

// The popup shows the local score first and keeps aria-busy="true" until the
// backend answers or fails. Waiting for the first score instead (what this used
// to do) captured that in-flight state whenever /analyze took longer than the
// fixed delay after it, which is why a Refresh click never helped: the score was
// already on screen, so the wait returned at once and captured the same state.
async function waitForFinalResult(popupPage) {
  await popupPage.waitForSelector('main.popup-shell[aria-busy="false"] .mode-banner', { timeout: 20000 });
  // This window is exactly the popup's 380px width, so a vertical scrollbar would
  // eat into it and add a horizontal one the real toolbar popup never shows.
  await popupPage.addStyleTag({ content: "html { scrollbar-width: none; }" });
  await popupPage.waitForTimeout(300); // let the last render settle before the screenshot
  return popupPage.locator(".mode-banner").innerText();
}

async function setBackendUrl(worker, backendBaseUrl) {
  await worker.evaluate(
    ([key, url]) => chrome.storage.sync.set({ [key]: { backendBaseUrl: url, requestTimeoutMs: 2500, dangerOverlayEnabled: true } }),
    [SETTINGS_KEY, backendBaseUrl],
  );
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
    await setBackendUrl(worker, shot.backendOff ? UNREACHABLE_BACKEND : "http://localhost:8000");
    await main.bringToFront();
    await main.goto(shot.url, { waitUntil: "networkidle" });
    await main.waitForTimeout(500);

    const realTab = await getRealDemoTab(worker);
    const popup = await openPopup(context, main, extensionId, realTab);
    const banner = await waitForFinalResult(popup);
    const backendAnswered = !banner.includes("unavailable");
    if (backendAnswered === Boolean(shot.backendOff)) {
      throw new Error(
        `${shot.name}: expected ${shot.backendOff ? "no backend" : "a backend result"}, popup says "${banner}". ` +
          "Is the backend running on http://localhost:8000?",
      );
    }
    const score = await popup.locator(".risk-panel").innerText();
    console.log(`  ${shot.name}: ${score.replace(/\s+/g, " ").trim()} (${banner})`);

    await popup.screenshot({ path: path.join(FRAMES_DIR, `${shot.name}-popup.png`) });

    await main.bringToFront();
    if (shot.overlayDoc) {
      await main.waitForSelector("#phishlens-warning-overlay", { timeout: 5000 });
      await main.waitForTimeout(500);
      await main.screenshot({ path: path.join(FRAMES_DIR, `${shot.name}-overlay.png`) });
    } else {
      await main.screenshot({ path: path.join(FRAMES_DIR, `${shot.name}-page.png`) });
    }

    await popup.close();
  }

  await context.close();
  console.log("Frames written to", FRAMES_DIR);

  if (WRITE_DOCS) {
    for (const shot of SHOTS) {
      fs.copyFileSync(path.join(FRAMES_DIR, `${shot.name}-popup.png`), path.join(DOCS_SCREENSHOTS_DIR, shot.doc));
      if (shot.overlayDoc) {
        fs.copyFileSync(path.join(FRAMES_DIR, `${shot.name}-overlay.png`), path.join(DOCS_SCREENSHOTS_DIR, shot.overlayDoc));
      }
    }
    console.log("README screenshots written to", DOCS_SCREENSHOTS_DIR);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
