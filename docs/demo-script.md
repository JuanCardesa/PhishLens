# Demo Script

This script demonstrates PhishLens without visiting suspicious external sites or using a real PhishTank key.

## Setup

1. Start the backend with the local demo threat source enabled:

   ```bash
   $env:PHISHLENS_ENABLE_DEMO_THREAT_SOURCE="true"
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
   ```

2. Start the local demo pages in a second terminal:

   ```bash
   python demo/serve_demo.py
   ```

3. Build and load the extension:

   ```bash
   cd extension
   npm install
   npm run build
   ```

   Load `extension/dist` from `chrome://extensions` with Developer mode enabled.

4. Open PhishLens settings from the popup and confirm:

   - Backend URL: `http://localhost:8000`.
   - Timeout: `2500`.
   - Danger overlay: enabled.

## Walkthrough

1. Open `http://127.0.0.1:8080/pages/safe.html`.
   Confirm a low-risk result and the `Backend enriched` state.

2. Open `http://127.0.0.1:8080/pages/suspicious.html`.
   Confirm the popup explains form, iframe, or external-link signals and shows category scores such as URL, Page structure, TLS, Threat intelligence, and ML.

3. Open `http://127.0.0.1:8080/pages/phishlens-demo-dangerous-login-secure-update.html`.
   Confirm the final label is `dangerous` and the dismissible overlay appears.

4. Stop the backend and reopen the popup on a demo page.
   Confirm the analysis still works and the UI shows `Backend unavailable`.

5. Restart the backend and use popup feedback:

   - `Mark as safe` for suspected false positives.
   - `Mark as phishing` for suspected false negatives.

6. Use `Copy report`.
   Confirm the copied text contains host-level context and excludes full URLs, form values, page text, cookies, screenshots, and HTML.

7. Inspect diagnostics:

   ```bash
   curl http://localhost:8000/diagnostics
   ```

   Confirm the payload contains counters only, not URLs or page content.

8. Inspect the structured analyze response:

   ```bash
   curl -X POST http://localhost:8000/analyze `
     -H "Content-Type: application/json" `
     -d "{\"url\":\"http://127.0.0.1:8080/pages/suspicious.html\",\"dom_features\":{\"has_password_field\":true,\"num_forms\":1,\"external_form_action\":false,\"num_iframes\":1,\"external_links_ratio\":0.2,\"has_hidden_inputs\":true}}"
   ```

   Confirm `risk_breakdown` includes URL, DOM, threat intelligence, TLS, and ML entries with category scores and caps.

## Talking Points

- Local analysis works without the backend.
- Backend enrichment adds TLS, threat intelligence, ML when available, and a dev-only demo threat source.
- The score is explainable by category through `risk_breakdown`, while `reasons` remains for compatibility.
- Feedback is logged without persistence and without page content.
- Diagnostics expose counters only and are intended for development environments.
