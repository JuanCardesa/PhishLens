# Chrome Web Store Listing Copy

Ready-to-paste text for the Chrome Developer Dashboard.
Review and localise before submission — do not claim more than the tool actually does.

---

## Extension name

```
PhishLens
```

---

## Short description (132 chars max)

```
Analyse any page for phishing risk in real time — local heuristics, TLS checks, and optional threat intelligence.
```
*(113 chars)*

---

## Detailed description (16 000 chars max)

```
PhishLens is a defensive browser extension that helps you evaluate whether a page might be a phishing attempt before you interact with it.

HOW IT WORKS

PhishLens can run local page-structure checks for its badge on HTTP/HTTPS pages. When you open the popup, it shows the current analysis and can add optional backend enrichment:

1. Local heuristics — instant, private, no backend calls
   • URL signals: look-alike domains of frequently impersonated brands (typosquatting such as paypa1.com, and Unicode homographs that swap in look-alike characters), a brand's full domain hidden in subdomains, labels mixing writing scripts, length, dot/hyphen density, IP-based domains, @ symbols, suspicious keywords in the hostname and path, and Shannon entropy of the domain name.
   • Page-structure signals: presence of login forms, password fields, forms that submit data to external domains, iframes, hidden inputs, the ratio of external links, and local brand-mismatch booleans derived from limited page metadata.

2. Optional backend enrichment from the popup — richer signals when you run the companion API
   • TLS certificate validation and expiry check for the current domain, plus Certificate Transparency logs to flag domains whose first certificate is less than a week old.
   • Domain registration age via RDAP: domains registered in the last 30 or 180 days add risk.
   • PhishTank threat-intelligence lookup (requires a free API key on your self-hosted backend).
   • A small machine-learning adjustment (−5 to +12 points) from a model trained on URL-derived numeric features.

Results are shown as a risk score (0–100) labelled Safe, Suspicious, or Dangerous, with a per-category breakdown explaining exactly what contributed to the score.

PRIVACY FIRST

PhishLens is built around minimal data collection:
• Only the current page URL and a small set of non-sensitive DOM counts and booleans are ever sent to the backend.
• Passwords, typed emails, form values, full HTML, cookies, session tokens, and browser history are never read or transmitted.
• Limited page metadata (document title, site name, first heading, and favicon URL) is inspected locally only to derive brand-mismatch booleans. Raw page text is never sent, logged, stored, or included in feedback.
• The backend does not persist analysis requests.
• Optional feedback (marking a result as safe or phishing) sends URL, observed label, and expected label. The self-hosted backend stores only hostname-level label metadata, note presence, request ID, and timestamp — no full URL, note text, or page content.

EXPLAINABILITY

Every risk score comes with a structured breakdown. You can see exactly how many points each category (URL, page structure, threat intelligence, TLS, domain age, ML) contributed, and why. There are no black-box verdicts.

OFFLINE FIRST

The local heuristic layer works without any network connection or backend. The extension falls back gracefully when the optional companion API is unavailable.

DANGER OVERLAY

For pages scored as Dangerous, an optional on-page warning overlay can be enabled from the settings page. It is dismissible and shows the top contributing signals.

LIMITATIONS

PhishLens is a risk-assistance tool, not a definitive phishing detector. It may produce false positives on legitimate pages and can miss novel or obfuscated phishing campaigns. Always apply your own judgement.

The ML model shipped with the companion API is trained on a real PhishTank + Tranco dataset, but that dataset has no DOM features (URLs only, no live browser session) and reflects a single snapshot in time. In validation it caught under half of phishing newer than its training data, which is why it can only move the score by a few points. Phishing campaigns evolve quickly, so the model should be retrained periodically.

SELF-HOSTING

The optional backend is open-source (FastAPI + Python) and designed to run locally or on your own infrastructure. The extension itself only calls the backend you configure; optional backend enrichment may call PhishTank, rdap.org, and crt.sh. No data is sent to Anthropic.

SOURCE CODE

https://github.com/JuanCardesa/PhishLens
```

---

## Category

**Primary:** Productivity  
**Secondary:** Security (if available as a tag)

---

## Screenshots required by the store

The store takes 1280×800 or 640×400 screenshots (PNG or JPEG). Generate them from real captures of the built extension on the local demo pages, with the backend and `demo/serve_demo.py` running (see [Local Demo](../README.md#local-demo)):

```bash
cd extension
npm run build
node scripts/record-demo.mjs --docs   # real popup and overlay captures
node scripts/take-screenshots.mjs     # frames them at 1280×800
```

| File in `docs/screenshots/` | What it shows |
|---|---|
| `01-safe-result.png` | Popup, `demo/pages/safe.html`, backend enriched |
| `02-suspicious-result.png` | Popup, `demo/pages/suspicious.html`, backend enriched |
| `03-dangerous-result.png` | Popup, the dangerous demo page, backend enriched |
| `04-local-only.png` | Popup with the backend unreachable (local analysis only) |
| `05-danger-overlay.png` | The in-page warning overlay on the dangerous demo page |

Do not hand-edit these images or draw popup states that the code does not render. Earlier versions were hand-built HTML mockups and drifted from the product. An options-page screenshot is not generated; capture it manually if you want one.

Minimum: 1 screenshot. Recommended: all 5 for a complete listing.

---

## Single promotional tile (optional, 440×280 PNG)

Suggested design: dark navy background (#132238), centred PhishLens logo (128px), tagline "Real-time phishing risk — explained" in white below.

---

## Support URL

```
https://github.com/JuanCardesa/PhishLens/issues
```

---

## Privacy policy URL

```
https://juancardesa.github.io/PhishLens/privacy/
```

*(Requires GitHub Pages to be enabled on main → docs/ folder — see docs/privacy/index.html)*

---

## Permissions justification (for the review form)

| Permission | Justification |
|------------|---------------|
| `activeTab` | Reads the URL of the current tab when the user opens the popup. No background scanning. |
| `scripting` | Injects the dismissible warning overlay after a Dangerous result, only when the overlay setting is enabled. |
| `storage` | Stores extension settings (backend URL, timeout, overlay toggle) and a short-lived local analysis cache. |
| `http://localhost:8000/*` | Calls the user's self-hosted companion API running on the default local port. |
| `http://127.0.0.1:8000/*` | Same as above for users who run the backend on the loopback IP. |
| `http://*/*`, `https://*/*` (optional) | Allows users to configure a non-localhost backend URL from the options page. Requested only when the user saves a custom backend URL. |
