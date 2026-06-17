/**
 * Generates Chrome Web Store screenshots (1280×800) for PhishLens.
 * Each screenshot shows the popup UI in a different state on a branded background.
 *
 * Usage: node scripts/take-screenshots.mjs
 * Output: docs/screenshots/*.png
 */

import { chromium } from "playwright";
import { mkdirSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dir, "..");
const repoRoot = resolve(root, "..");
const outDir = resolve(repoRoot, "docs", "screenshots");
mkdirSync(outDir, { recursive: true });

const CSS = readFileSync(resolve(root, "src", "popup", "popup.css"), "utf8");

const BRAND = {
  navy: "#132238",
  teal: "#3aa6b9",
  gold: "#f4b942",
  light: "#f8fafc",
};

function page(title, bannerClass, bannerText, panelClass, statusText, score, url, confidence, mode, sources, primarySignal, groups, feedbackDisabled = false) {
  const sourceSpans = sources.map((s) => `<span>${s}</span>`).join("");
  const groupHtml = groups
    .map(
      (g) => `
      <section class="signal-group">
        <h3><span>${g.title}</span><strong>${g.score}</strong></h3>
        <ul>${g.reasons.map((r) => `<li>${r}</li>`).join("")}</ul>
      </section>`,
    )
    .join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    ${CSS}
    html, body { margin: 0; padding: 0; width: 1280px; height: 800px; overflow: hidden; }
    body { background: ${BRAND.navy}; display: flex; align-items: center; justify-content: center; }
    .frame {
      background: #f5f7fb;
      border-radius: 12px;
      box-shadow: 0 24px 64px rgba(0,0,0,0.45);
      overflow: hidden;
      width: 380px;
    }
    .chrome-bar {
      background: #e8eaed;
      height: 36px;
      display: flex;
      align-items: center;
      padding: 0 12px;
      gap: 6px;
      border-bottom: 1px solid #d3d3d3;
    }
    .chrome-dot { width: 10px; height: 10px; border-radius: 50%; }
    .chrome-dot:nth-child(1) { background: #f4b942; }
    .chrome-dot:nth-child(2) { background: #9ad7ba; }
    .chrome-dot:nth-child(3) { background: #f08a80; }
    .chrome-title { margin-left: 8px; font-size: 11px; color: #5f6368; font-family: system-ui; font-weight: 600; }
    .tagline {
      position: absolute;
      bottom: 32px;
      left: 50%;
      transform: translateX(-50%);
      color: rgba(248,250,252,0.45);
      font-family: system-ui, sans-serif;
      font-size: 13px;
      white-space: nowrap;
      letter-spacing: 0.02em;
    }
  </style>
</head>
<body>
  <div class="frame">
    <div class="chrome-bar">
      <div class="chrome-dot"></div>
      <div class="chrome-dot"></div>
      <div class="chrome-dot"></div>
      <span class="chrome-title">PhishLens</span>
    </div>
    <main class="popup-shell">
      <header class="header">
        <div>
          <p class="eyebrow">PhishLens</p>
          <h1>Page risk</h1>
        </div>
        <div class="header-actions">
          <button class="tool-button" type="button">Settings</button>
          <button class="tool-button" type="button">Refresh</button>
        </div>
      </header>

      <div class="mode-banner ${bannerClass}">${bannerText}</div>

      <section class="risk-panel ${panelClass}">
        <div>
          <span class="status">${statusText}</span>
          <strong class="score">${score}</strong>
        </div>
        <span class="score-label">risk score</span>
      </section>

      <section class="details">
        <div class="url-block">
          <span>URL</span>
          <p>${url}</p>
        </div>
        <div class="meta-grid">
          <div><span>Confidence</span><strong>${confidence}</strong></div>
          <div><span>Backend</span><strong>${mode}</strong></div>
        </div>
        <div class="source-list">${sourceSpans}</div>
      </section>

      <section class="reasons">
        <h2>Signals</h2>
        <p class="primary-signal">${primarySignal}</p>
        <div class="signal-groups">${groupHtml}</div>
      </section>

      <section class="feedback">
        <h2>Feedback</h2>
        <div class="feedback-actions">
          <button type="button" ${feedbackDisabled ? "disabled" : ""}>Mark as safe</button>
          <button type="button" ${feedbackDisabled ? "disabled" : ""}>Mark as phishing</button>
        </div>
      </section>
    </main>
  </div>
  <span class="tagline">PhishLens · Defensive phishing risk analysis</span>
</body>
</html>`;
}

const SCREENSHOTS = [
  {
    file: "01-safe-result.png",
    title: "Safe result",
    html: page(
      "Safe result",
      "backend-enriched",
      "Backend enrichment is active for this result.",
      "safe",
      "Safe",
      12,
      "https://example.com/",
      "87%",
      "Backend enriched",
      ["heuristics", "tls", "ml"],
      "URL: No high-risk signals were detected",
      [
        { title: "URL", score: "3/35", reasons: ["URL does not use HTTPS"] },
        { title: "Page structure", score: "0/30", reasons: ["No high-risk signals were detected"] },
        { title: "Threat intelligence", score: "0/40", reasons: ["Threat intelligence did not add high-risk signals"] },
        { title: "TLS", score: "0/15", reasons: ["TLS did not add high-risk signals"] },
        { title: "ML", score: "−9 (−10 to +20)", reasons: ["Machine learning model reduced the estimated risk"] },
      ],
    ),
  },
  {
    file: "02-suspicious-result.png",
    title: "Suspicious result",
    html: page(
      "Suspicious result",
      "backend-enriched",
      "Backend enrichment is active for this result.",
      "suspicious",
      "Suspicious",
      48,
      "http://secure-account-verify.example.net/login",
      "72%",
      "Backend enriched",
      ["heuristics", "tls", "ml"],
      "URL: URL contains multiple hyphens",
      [
        { title: "URL", score: "28/35", reasons: ["URL contains multiple hyphens", "Domain or path contains suspicious keywords", "URL does not use HTTPS", "URL contains many subdomains"] },
        { title: "Page structure", score: "4/30", reasons: ["Page contains forms"] },
        { title: "Threat intelligence", score: "0/40", reasons: ["Threat intelligence did not add high-risk signals"] },
        { title: "TLS", score: "10/15", reasons: ["TLS certificate could not be validated"] },
        { title: "ML", score: "+6 (−10 to +20)", reasons: ["Machine learning model increased the estimated risk"] },
      ],
    ),
  },
  {
    file: "03-dangerous-result.png",
    title: "Dangerous result",
    html: page(
      "Dangerous result",
      "backend-enriched",
      "Backend enrichment is active for this result.",
      "dangerous",
      "Dangerous",
      91,
      "http://xn--pypl-ppa.com/login/verify-account-update",
      "95%",
      "Backend enriched",
      ["heuristics", "tls", "phishtank", "ml"],
      "Threat intelligence: URL appears in a verified phishing intelligence feed",
      [
        { title: "URL", score: "35/35", reasons: ["URL uses punycode", "Domain or path contains suspicious keywords", "URL does not use HTTPS"] },
        { title: "Page structure", score: "22/30", reasons: ["Page contains a password field", "Form submits data to an external domain", "Page contains forms"] },
        { title: "Threat intelligence", score: "40/40", reasons: ["URL appears in a verified phishing intelligence feed"] },
        { title: "TLS", score: "0/15", reasons: ["TLS certificate could not be validated"] },
        { title: "ML", score: "+20 (−10 to +20)", reasons: ["Machine learning model increased the estimated risk"] },
      ],
    ),
  },
  {
    file: "04-local-only.png",
    title: "Local-only fallback",
    html: page(
      "Local-only fallback",
      "backend-unavailable",
      "Backend unavailable. Showing local fallback analysis.",
      "suspicious",
      "Suspicious",
      35,
      "http://paypal-secure.update-account.net/verify",
      "60%",
      "Local only",
      ["heuristics"],
      "URL: URL contains multiple hyphens",
      [
        { title: "URL", score: "35/35", reasons: ["URL contains multiple hyphens", "Domain or path contains suspicious keywords", "URL does not use HTTPS", "URL contains many subdomains"] },
        { title: "Page structure", score: "0/30", reasons: ["No high-risk signals were detected"] },
        { title: "Threat intelligence", score: "0/40", reasons: ["Threat intelligence was not available for this result"] },
        { title: "TLS", score: "0/15", reasons: ["TLS analysis was not available for this result"] },
        { title: "ML", score: "0 (−10 to +20)", reasons: ["ML model was not available; heuristic scoring was used"] },
      ],
    ),
  },
];

// Overlay screenshot uses a different layout
const OVERLAY_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body { margin: 0; padding: 0; width: 1280px; height: 800px; overflow: hidden; }
    body {
      font-family: Inter, system-ui, sans-serif;
      background: #f5f7fb;
      position: relative;
    }
    /* Simulated page content behind overlay */
    .fake-page {
      padding: 40px 60px;
      color: #172033;
    }
    .fake-page h1 { font-size: 28px; margin-bottom: 12px; }
    .fake-page p { font-size: 15px; color: #526070; max-width: 600px; margin-bottom: 16px; }
    .fake-form { max-width: 360px; }
    .fake-form label { display: block; font-size: 13px; font-weight: 700; margin-bottom: 4px; color: #344054; }
    .fake-form input { width: 100%; height: 36px; border: 1px solid #d0d5dd; border-radius: 6px; margin-bottom: 12px; padding: 0 10px; font-size: 14px; }
    .fake-form button { height: 40px; padding: 0 20px; background: #132238; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 700; cursor: pointer; }
    /* Overlay */
    .phishlens-overlay {
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(19,34,56,0.72);
      display: flex; align-items: center; justify-content: center;
      backdrop-filter: blur(2px);
    }
    .phishlens-dialog {
      background: #fff;
      border: 2px solid #f08a80;
      border-radius: 14px;
      padding: 28px 32px;
      max-width: 420px;
      width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,0.35);
    }
    .phishlens-dialog-eyebrow {
      font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
      text-transform: uppercase; color: #c0392b; margin-bottom: 6px;
    }
    .phishlens-dialog h2 {
      font-size: 20px; font-weight: 700; color: #172033; margin: 0 0 6px;
    }
    .phishlens-score-row {
      display: flex; align-items: baseline; gap: 8px; margin-bottom: 16px;
    }
    .phishlens-score {
      font-size: 48px; font-weight: 700; line-height: 1; color: #c0392b;
    }
    .phishlens-score-label { font-size: 12px; font-weight: 700; color: #526070; text-transform: uppercase; }
    .phishlens-reasons { margin-bottom: 20px; padding-left: 18px; }
    .phishlens-reasons li { font-size: 13px; color: #344054; margin-bottom: 4px; line-height: 1.4; }
    .phishlens-actions { display: flex; gap: 10px; }
    .phishlens-btn {
      flex: 1; height: 38px; border-radius: 8px; font-size: 13px; font-weight: 700;
      border: none; cursor: pointer;
    }
    .phishlens-btn-dismiss { background: #f5f7fb; color: #172033; border: 1px solid #d0d5dd; }
    .phishlens-btn-back { background: #132238; color: #fff; }
  </style>
</head>
<body>
  <div class="fake-page">
    <h1>Verify your account</h1>
    <p>Please sign in to confirm your identity and secure your account.</p>
    <div class="fake-form">
      <label>Email address</label>
      <input type="email" placeholder="you@example.com"/>
      <label>Password</label>
      <input type="password" placeholder="••••••••"/>
      <button>Sign in</button>
    </div>
  </div>
  <div class="phishlens-overlay">
    <div class="phishlens-dialog">
      <p class="phishlens-dialog-eyebrow">PhishLens warning</p>
      <h2>High phishing risk detected</h2>
      <div class="phishlens-score-row">
        <span class="phishlens-score">91</span>
        <span class="phishlens-score-label">risk score</span>
      </div>
      <ul class="phishlens-reasons">
        <li>URL appears in a verified phishing intelligence feed</li>
        <li>URL uses punycode</li>
        <li>Form submits data to an external domain</li>
        <li>Page contains a password field</li>
      </ul>
      <div class="phishlens-actions">
        <button class="phishlens-btn phishlens-btn-dismiss">Dismiss</button>
        <button class="phishlens-btn phishlens-btn-back">Go back</button>
      </div>
    </div>
  </div>
</body>
</html>`;

async function run() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });

  for (const shot of SCREENSHOTS) {
    const p = await context.newPage();
    await p.setContent(shot.html, { waitUntil: "networkidle" });
    await p.waitForTimeout(300);
    const outPath = resolve(outDir, shot.file);
    await p.screenshot({ path: outPath, fullPage: false });
    console.log(`  ✓ ${shot.file}`);
    await p.close();
  }

  // Overlay screenshot
  const overlayPage = await context.newPage();
  await overlayPage.setContent(OVERLAY_HTML, { waitUntil: "networkidle" });
  await overlayPage.waitForTimeout(300);
  const overlayPath = resolve(outDir, "05-danger-overlay.png");
  await overlayPage.screenshot({ path: overlayPath, fullPage: false });
  console.log("  ✓ 05-danger-overlay.png");
  await overlayPage.close();

  await browser.close();
  console.log(`\nScreenshots saved to ${outDir}`);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
