# Chrome Web Store Readiness

This checklist prepares PhishLens for a future Chrome Web Store submission. Review the official Chrome Web Store documentation before every real submission because store requirements can change.

## Package

- Build from `main`.
- Run backend and extension checks.
- Run `cd extension && npm run package`.
- Upload the generated `extension/release/phishlens-extension-v*.zip`.
- Do not upload source maps, local `.env` files, cache folders, or generated model artifacts.

## Store Listing

Prepare:

- extension name: `PhishLens`,
- short description focused on defensive phishing risk analysis,
- detailed description explaining local heuristics, optional backend enrichment, and limitations,
- screenshots of popup, options page, and warning overlay,
- support/contact URL if available,
- category aligned with security/productivity tooling.

Avoid claims that PhishLens is a definitive phishing detector. It is an explainable risk-assistance tool.

## Privacy Disclosure

The listing should match [privacy.md](privacy.md):

- collected data is limited to current URL, derived URL features, non-sensitive DOM features, optional feedback labels, TLS metadata, threat-intel result, and aggregate diagnostics;
- credentials, typed emails, form values, cookies, tokens, screenshots, full HTML, browser history, and private page text are not collected;
- API keys are backend-only and never bundled with the extension;
- feedback is stored in SQLite (hostname, label, note presence, request ID, and timestamp only — no full URLs, form values, or personal data).

## Permissions Justification

Use [permissions.md](permissions.md) as the source of truth for the Web Store permission explanations.

Before publishing, confirm:

- no new required permissions were added without documentation,
- optional host permissions are still user-initiated,
- no `<all_urls>` permission was introduced,
- custom backend access still falls back safely when denied.

## Review Notes

Document these points for reviewers:

- PhishLens is defensive-only.
- The demo threat source is localhost-only and disabled by default.
- Backend diagnostics are aggregate counters and do not expose full URLs or page content.
- TLS analysis is performed from the backend and may differ from browser certificate state behind proxies or TLS inspection.
- The ML model is trained on a real PhishTank + Tranco dataset (see docs/ml-methodology.md), but it has no DOM features and reflects a single point-in-time snapshot; it should be retrained periodically.

## Release Flow

1. Merge feature work into `develop`.
2. Promote `develop` to `main` through a release PR.
3. Tag from `main`.
4. Let `Release Extension` attach the ZIP artifact to GitHub Releases.
5. Use that ZIP for Web Store review.

## Official References

- Publish in the Chrome Web Store: https://developer.chrome.com/docs/webstore/publish
- Chrome Web Store privacy practices: https://developer.chrome.com/docs/webstore/program-policies/privacy
- Declare extension permissions: https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
