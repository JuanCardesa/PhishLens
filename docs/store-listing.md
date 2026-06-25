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
   • URL signals: length, dot/hyphen density, IP-based domains, @ symbols, suspicious keywords in the hostname and path, punycode characters, and Shannon entropy of the domain name.
   • Page-structure signals: presence of login forms, password fields, forms that submit data to external domains, iframes, hidden inputs, the ratio of external links, and local brand-mismatch booleans derived from limited page metadata.

2. Optional backend enrichment from the popup — richer signals when you run the companion API
   • TLS certificate validation and expiry check for the current domain.
   • PhishTank threat-intelligence lookup (requires a free API key on your self-hosted backend).
   • Machine-learning model adjustment trained on URL-derived numeric features.

Results are shown as a risk score (0–100) labelled Safe, Suspicious, or Dangerous, with a per-category breakdown explaining exactly what contributed to the score.

PRIVACY FIRST

PhishLens is built around minimal data collection:
• Only the current page URL and a small set of non-sensitive DOM counts and booleans are ever sent to the backend.
• Passwords, typed emails, form values, full HTML, cookies, session tokens, and browser history are never read or transmitted.
• Limited page metadata (document title, site name, first heading, and favicon URL) is inspected locally only to derive brand-mismatch booleans. Raw page text is never sent, logged, stored, or included in feedback.
• The backend does not persist analysis requests.
• Optional feedback (marking a result as safe or phishing) sends URL, observed label, and expected label. The self-hosted backend stores only hostname-level label metadata, note presence, request ID, and timestamp — no full URL, note text, or page content.

EXPLAINABILITY

Every risk score comes with a structured breakdown. You can see exactly how many points each category (URL, page structure, TLS, threat intelligence, ML) contributed, and why. There are no black-box verdicts.

OFFLINE FIRST

The local heuristic layer works without any network connection or backend. The extension falls back gracefully when the optional companion API is unavailable.

DANGER OVERLAY

For pages scored as Dangerous, an optional on-page warning overlay can be enabled from the settings page. It is dismissible and shows the top contributing signals.

LIMITATIONS

PhishLens is a risk-assistance tool, not a definitive phishing detector. It may produce false positives on legitimate pages and can miss novel or obfuscated phishing campaigns. Always apply your own judgement.

The ML model shipped with the companion API is trained on a real PhishTank + Tranco dataset, but that dataset has no DOM features (URLs only, no live browser session) and reflects a single snapshot in time — phishing campaigns evolve quickly, so the model should be retrained periodically.

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

The following screenshots must be created manually at 1280×800 or 640×400 (PNG or JPEG):

| # | What to capture | Suggested state |
|---|-----------------|-----------------|
| 1 | Popup — Safe result | Navigate to https://example.com, open popup |
| 2 | Popup — Suspicious result | Navigate to a URL with many hyphens and a login keyword |
| 3 | Popup — Dangerous result with risk breakdown expanded | Use the local demo page |
| 4 | Options page | Open settings with a custom backend URL filled in |
| 5 | Danger overlay | Trigger a dangerous result with overlay enabled |

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
