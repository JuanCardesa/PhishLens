# PhishLens Local Demo

This folder contains safe, non-offensive pages for a reproducible extension walkthrough.

## Run The Demo Pages

From the repository root:

```bash
python demo/serve_demo.py
```

Open:

- `http://localhost:8080/pages/safe.html` (Safe)
- `http://localhost:8080/pages/suspicious.html` (Suspicious)
- `http://localhost:8080/pages/phishlens-demo-dangerous-login-secure-update.html` (Dangerous)

Use `localhost`, not `127.0.0.1`. The backend rejects private IP literals as an SSRF safeguard, so on `127.0.0.1` the popup never gets a backend result. The IP host would also add URL risk points the demo is not meant to show.

Each page shows its label in local-only mode as well as with the backend. `suspicious.html` is tuned to stay Suspicious for any ML adjustment; the comment in the page explains the arithmetic. `extension/e2e/smoke.mjs` loads all three pages in real Chromium and checks the label of each.

For the dangerous page to also show the threat-intelligence signal without a real threat-intelligence key, run the backend with:

```bash
PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true
```

The demo threat source only matches localhost/127.0.0.1 URLs containing `phishlens-demo-dangerous`.
It does not collect credentials, form values, page text, screenshots, or HTML.
