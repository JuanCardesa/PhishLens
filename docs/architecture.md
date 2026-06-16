# Architecture

PhishLens has three main runtime parts:

```text
Browser tab
  -> content script
  -> popup UI and options page
  -> FastAPI backend
  -> optional PhishTank, TLS socket inspection, and local ML model
  -> development diagnostics and rate limiting
```

## Analysis Flow

1. The user opens the extension popup.
2. The popup reads the active tab URL through Chrome APIs.
3. The content script returns only technical DOM features:
   number of forms, password field presence, external form action, iframe count, external link ratio, and hidden input presence.
4. The popup computes a local fallback score.
5. The popup reads backend settings from `chrome.storage.sync`.
6. The popup calls `POST /analyze` when the configured backend is available.
7. The backend normalizes the URL, removes fragments, and combines URL heuristics, DOM signals, optional PhishTank, TLS checks, and optional ML adjustment.
8. PhishTank and TLS checks use short in-memory TTL caches to reduce repeated external calls.
9. In development demo mode, localhost URLs containing `phishlens-demo-dangerous` can trigger an explicit demo threat signal.
10. The popup displays score, label, confidence, reasons, source mode, and feedback controls.
11. A `dangerous` final result can inject a dismissible page overlay when enabled.
12. `/diagnostics` exposes aggregate counters only when diagnostics are enabled.

## Extension And Backend Boundary

The extension does not send full HTML or form values. The backend receives the URL and structured DOM features only.

Feedback uses the same privacy boundary. The popup sends URL, observed label, expected label, and a short non-sensitive note. The backend logs host-level context and does not persist feedback in the MVP.

## Configuration Flow

The options page stores:

- Backend base URL.
- Backend request timeout.
- Whether the dangerous-result overlay is enabled.

Custom remote backend origins use optional host permissions instead of broad default host access.

## Request Context And Diagnostics

The backend adds an `X-Request-ID` header to every response. A caller-provided `X-Request-ID` is accepted only when it is short and uses safe characters; otherwise the backend generates one.

`/diagnostics` is intended for development and demo workflows. It reports counters for analysis requests, feedback, rate limits, labels, sources, cache hits/misses, and external service skips/errors. It does not expose URLs, page text, form values, credentials, cookies, screenshots, or HTML.

## Rate Limiting

`/analyze` and `/report` use process-local in-memory rate limits keyed by route and client host. This is a lightweight development safeguard, not a distributed production limiter.

## TLS In Backend

Chrome extensions cannot reliably inspect full certificate details from page scripts. PhishLens performs TLS checks from the backend using Python sockets and the system trust store.

This can differ from what the browser sees when the user is behind a corporate proxy, local antivirus TLS inspection, captive portal, or custom trust store.

## Text Diagram

```text
[Chrome tab]
    |
    | DOM counts only
    v
[Content script] ---- message ----> [Popup React UI]
                                     |
                                     | settings
                                     v
                              [Options page]
                                     |
                                     | POST /analyze
                                     v
                             [FastAPI backend]
                              |      |       |        |
                              v      v       v        v
                         [PhishTank] [TLS] [ML model] [Diagnostics]
                              ^      ^
                              |      |
                            TTL cache
```
