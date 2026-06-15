# Privacy

PhishLens is designed to minimize data collection.

## Processed Data

- Current page URL.
- Structured URL features derived from that URL.
- DOM counts and booleans:
  forms, password field presence, external form action, iframes, external link ratio, and hidden input presence.
- Optional backend TLS certificate metadata for the domain.
- Optional PhishTank lookup result for the URL.
- Optional user feedback labels from the popup: observed label, expected label, and a short non-sensitive note.

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

## Storage

The extension stores short-lived cached analysis results keyed by a local hash of the URL. The MVP backend does not persist `/analyze` requests or `/report` feedback.

The extension stores backend settings in `chrome.storage.sync`: backend URL, timeout, and overlay preference.

The backend uses short-lived in-memory caches for PhishTank URL lookups and TLS hostname checks. These caches are process-local and are not durable storage.

## Feedback

Popup feedback exists to support future false positive and false negative review. In this sprint, `/report` logs only host-level context, labels, and whether a note was present. It does not store credentials, form values, page content, or full HTML.

## API Keys

PhishTank keys are backend environment variables only. They must never be placed in the frontend or extension bundle.
