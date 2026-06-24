# Extension Permissions

PhishLens keeps Chrome permissions narrow and documents every permission used by the Manifest V3 extension.

Reviewed for v0.3.0: no permission changes. The manifest version bump is documentation-only.

## Required Permissions

| Permission | Why PhishLens Uses It |
| --- | --- |
| `activeTab` | Reads the URL of the current active tab only when the user opens or refreshes the popup. |
| `scripting` | Injects the dismissible warning overlay after a final `dangerous` result when the overlay setting is enabled. |
| `storage` | Stores extension settings and short-lived local analysis cache entries. |

## Required Host Permissions

| Host Permission | Why PhishLens Uses It |
| --- | --- |
| `http://localhost:8000/*` | Calls the local development backend. |
| `http://127.0.0.1:8000/*` | Calls the local development backend when users run it on loopback IP. |

## Optional Host Permissions

| Optional Permission | Why PhishLens Uses It |
| --- | --- |
| `http://*/*` and `https://*/*` | Allows users to explicitly approve a custom backend origin from the options page. |

Optional host access is requested only when a user configures a non-default backend URL. If Chrome denies the permission request, PhishLens falls back to `http://localhost:8000`.

## Content Script Scope

The content script runs on HTTP and HTTPS pages to collect technical DOM counts and booleans:

- form count,
- password-field presence,
- external form action presence,
- iframe count,
- external link ratio,
- hidden input presence,
- a local brand-text mismatch boolean derived from document title, `og:site_name`, and first `h1`,
- a local favicon-hotlink boolean derived from the favicon URL.

On page load, the content script can send the current URL and these derived booleans/counts to the extension service worker for local badge scoring. This does not call the backend; backend enrichment runs from the popup.

The content script must not read passwords, typed emails, form values, full HTML, cookies, tokens, or screenshots. It may inspect the limited page metadata listed above only to derive booleans; raw page text is never transmitted, stored, logged, or included in reports.

## Browser-Specific Settings (Firefox)

`manifest.json` declares `browser_specific_settings.gecko` (an extension ID and minimum Firefox version). This is metadata Firefox uses to recognize and sign the extension consistently across updates — it does not grant any additional permission and Chrome ignores the key entirely. It is required for `browser.storage.sync` to work correctly in Firefox, which keys synced storage by extension ID.

## Extension Icons

`manifest.json` declares PNG icons at 16, 48, and 128 px (used by Chrome for the toolbar, extensions page, and Web Store). A 512 px PNG is generated alongside these for the Chrome Web Store promotional tile. Icon declarations are not permissions — they do not grant the extension any additional access to browser data or user pages.

## Content Security Policy

`manifest.json` declares an explicit `content_security_policy` for extension pages:

```
script-src 'self'; object-src 'none'
```

This restricts script execution to the extension's own bundled files and blocks embedded object elements. It matches and makes explicit the default MV3 security policy.

## Change Control

Any pull request that changes `extension/manifest.json` must also review and update this document. `PR Guardian` enforces that coupling.

## Official References

- Chrome extension permissions: https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
- Chrome optional permissions: https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions#optional_permissions
- Chrome Web Store publish guide: https://developer.chrome.com/docs/webstore/publish
