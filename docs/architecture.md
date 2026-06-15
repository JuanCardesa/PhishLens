# Architecture

PhishLens has three main runtime parts:

```text
Browser tab
  -> content script
  -> popup UI
  -> FastAPI backend
  -> optional PhishTank, TLS socket inspection, and local ML model
```

## Analysis Flow

1. The user opens the extension popup.
2. The popup reads the active tab URL through Chrome APIs.
3. The content script returns only technical DOM features:
   number of forms, password field presence, external form action, iframe count, external link ratio, and hidden input presence.
4. The popup computes a local fallback score.
5. The popup calls `POST /analyze` when `http://localhost:8000` is available.
6. The backend combines URL heuristics, DOM signals, optional PhishTank, TLS checks, and optional ML adjustment.
7. The popup displays score, label, confidence, and reasons.

## Extension And Backend Boundary

The extension does not send full HTML or form values. The backend receives the URL and structured DOM features only.

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
                                     | POST /analyze
                                     v
                             [FastAPI backend]
                              |      |       |
                              v      v       v
                         [PhishTank] [TLS] [ML model]
```
