# Threat Model

## Protected Assets

- User credentials and private form input.
- User browsing privacy.
- Backend API keys.
- Extension integrity.
- Risk scoring trustworthiness.

## Risks

- Overcollection of sensitive page data.
- API key exposure in the extension bundle.
- False positives on legitimate login pages.
- False negatives on new phishing campaigns.
- Backend dependency or threat-intel outage.
- Malicious pages attempting to confuse DOM feature extraction.

## Assumptions

- The extension is installed by the user in a trusted browser profile.
- The backend is controlled by the project owner.
- PhishTank availability and rate limits are not guaranteed.
- TLS analysis from the backend may not match the user's browser path.

## Possible Abuse

- Repurposing the extension to collect credentials.
- Adding remote code loading to bypass review.
- Sending full page content to the backend.
- Treating demo ML metrics as production evidence.

## Mitigations

- Minimum Chrome permissions.
- No form values or full HTML collection.
- Backend-only API keys.
- Explicit docs for limitations and privacy boundaries.
- Tests around scoring and schemas.
- Conventional commits and reviewable changes.
