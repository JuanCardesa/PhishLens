# PhishLens Local Demo

This folder contains safe, non-offensive pages for a reproducible extension walkthrough.

## Run The Demo Pages

From the repository root:

```bash
python demo/serve_demo.py
```

Open:

- `http://127.0.0.1:8080/pages/safe.html`
- `http://127.0.0.1:8080/pages/suspicious.html`
- `http://127.0.0.1:8080/pages/phishlens-demo-dangerous-login-secure-update.html`

For the dangerous page to deterministically cross the `dangerous` threshold without using a real threat-intelligence key, run the backend with:

```bash
PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true
```

The demo threat source only matches localhost/127.0.0.1 URLs containing `phishlens-demo-dangerous`.
It does not collect credentials, form values, page text, screenshots, or HTML.
