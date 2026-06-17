# Privacy

PhishLens is designed to minimize data collection.

## Processed Data

- Current page URL.
- Structured URL features derived from that URL.
- DOM counts and booleans:
  forms, password field presence, external form action, iframes, external link ratio, and hidden input presence.
- Optional backend TLS certificate metadata for the domain, including expiry status. An expired certificate is identified via the OpenSSL verify code (code 10 = `X509_V_ERR_CERT_HAS_EXPIRED`) rather than by reading the `notAfter` field, because the SSL handshake rejects expired certificates before the field is accessible.
- Optional PhishTank lookup result for the URL.
- Optional user feedback labels from the popup: observed label, expected label, and a short non-sensitive note.
- Aggregate diagnostics counters for request counts, labels, sources, rate limits, cache hits, and external-service skips/errors.
- Non-sensitive backend capability flags such as whether diagnostics, TLS analysis, threat intelligence, rate limiting, demo source, or ML model loading are enabled.

## Data Not Collected

PhishLens must not collect:

- Passwords.
- Typed emails.
- Form values.
- Full page HTML.
- Cookies.
- Session tokens.
- Browser history.
- Screenshots.
- Private page text.
- Full URLs in diagnostics.
- Local model paths in diagnostics.

## Storage

The extension stores short-lived cached analysis results keyed by a local hash of the URL. The MVP backend does not persist `/analyze` requests or `/report` feedback.

The extension stores backend settings in `chrome.storage.sync`: backend URL, timeout, and overlay preference.

The backend uses short-lived in-memory caches for PhishTank URL lookups and TLS hostname checks. These caches are process-local and are not durable storage.

Successful PhishTank results are cached for 300 seconds. Transient network errors from PhishTank are cached separately for 30 seconds to allow fast retries during brief outages without hammering the external API on every request.

Diagnostics and rate-limit counters are process-local and reset when the backend restarts.

## Feedback

Popup feedback is now persisted to a local SQLite database (`feedback.db` by default, configurable via `PHISHLENS_FEEDBACK_DB_PATH`). The store records only the URL hostname, the observed and expected risk labels, and a boolean indicating whether a note was present. Full URLs, note text, page content, form values, and credentials are never stored.

The mode banner in the popup UI explicitly lists which backend services (TLS, threat intelligence, ML) were not checked when the backend is unavailable, so users know the score is heuristic-only.

## Accessibility and Dark Mode

The popup UI supports the system `prefers-color-scheme: dark` media query via CSS custom properties. This is a purely visual change — no additional data is collected or transmitted based on the user's colour scheme preference.

The risk panel uses `aria-live="polite"` with `aria-atomic="true"` so screen readers announce the updated risk level and score when analysis completes. The risk level label (`Safe`, `Suspicious`, `Dangerous`) is rendered as visible text in addition to the colour-coded border; visible symbols marked `aria-hidden="true"` provide a colour-independent indicator for users with colour-vision deficiency. No user interaction data beyond what is already documented is captured by these accessibility additions.

## Diagnostics

`GET /diagnostics` is a development endpoint. It returns aggregate counters only. It must not include submitted URLs, form values, page content, cookies, credentials, screenshots, or HTML.

## Demo Threat Source

`PHISHLENS_ENABLE_DEMO_THREAT_SOURCE` enables a localhost-only signal for the reproducible demo page. It is disabled by default and does not represent PhishTank or any external intelligence feed.

## API Keys

PhishTank keys are backend environment variables only. They must never be placed in the frontend or extension bundle.
