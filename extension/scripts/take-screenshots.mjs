/**
 * Builds the Chrome Web Store screenshots (1280×800) for PhishLens by framing
 * real captures of the extension on a branded background.
 *
 * This used to hand-write an HTML copy of the popup filled with invented data,
 * which drifted from the product: it showed a "60%" confidence where the popup
 * now says "Heuristic", a "URL uses punycode" reason that no longer exists, ML
 * adjustments (−9, +6) the model can never produce, and an older overlay design.
 * Now every pixel of product UI comes from scripts/record-demo.mjs, so the store
 * images can only show what the extension really renders.
 *
 * Usage:
 *   node scripts/record-demo.mjs --docs   # capture docs/screenshots/popup-*.png + danger-overlay.png
 *   node scripts/take-screenshots.mjs     # frame them as docs/screenshots/0N-*.png
 */

import { chromium } from "playwright";
import { existsSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const screenshotsDir = resolve(__dir, "..", "..", "docs", "screenshots");

const SHOTS = [
  { file: "01-safe-result.png", source: "popup-safe.png", caption: "Safe page: backend-enriched result with a per-category breakdown" },
  { file: "02-suspicious-result.png", source: "popup-suspicious.png", caption: "Suspicious page: a sign-in form that posts to another domain" },
  { file: "03-dangerous-result.png", source: "popup-dangerous.png", caption: "Dangerous page: every signal that contributed, explained" },
  { file: "04-local-only.png", source: "popup-local-only.png", caption: "No backend: the same local analysis still runs offline" },
  { file: "05-danger-overlay.png", source: "danger-overlay.png", caption: "Dangerous pages get a dismissible in-page warning", wide: true },
];

function framedPage(imageDataUrl, caption, wide) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <style>
    html, body { margin: 0; width: 1280px; height: 800px; overflow: hidden; }
    body {
      background: #132238;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 28px;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    }
    img {
      display: block;
      max-height: ${wide ? 620 : 660}px;
      max-width: 1120px;
      border-radius: 12px;
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
    }
    p { margin: 0; color: rgba(248, 250, 252, 0.8); font-size: 20px; font-weight: 600; }
  </style>
</head>
<body>
  <img src="${imageDataUrl}" alt=""/>
  <p>${caption}</p>
</body>
</html>`;
}

async function run() {
  const missing = SHOTS.map((shot) => shot.source).filter((source) => !existsSync(resolve(screenshotsDir, source)));
  if (missing.length > 0) {
    throw new Error(`missing ${missing.join(", ")} in ${screenshotsDir}. Run "node scripts/record-demo.mjs --docs" first.`);
  }

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  for (const shot of SHOTS) {
    const image = readFileSync(resolve(screenshotsDir, shot.source)).toString("base64");
    await page.setContent(framedPage(`data:image/png;base64,${image}`, shot.caption, shot.wide), { waitUntil: "load" });
    await page.screenshot({ path: resolve(screenshotsDir, shot.file) });
    console.log(`  ✓ ${shot.file} (from ${shot.source})`);
  }

  await browser.close();
  console.log(`\nStore screenshots written to ${screenshotsDir}`);
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
