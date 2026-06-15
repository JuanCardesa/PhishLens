# Privacy

PhishLens is designed to minimize data collection.

## Processed Data

- Current page URL.
- Structured URL features derived from that URL.
- DOM counts and booleans:
  forms, password field presence, external form action, iframes, external link ratio, and hidden input presence.
- Optional backend TLS certificate metadata for the domain.
- Optional PhishTank lookup result for the URL.

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

## API Keys

PhishTank keys are backend environment variables only. They must never be placed in the frontend or extension bundle.
