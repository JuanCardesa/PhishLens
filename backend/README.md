# PhishLens Backend

FastAPI service for explainable phishing risk analysis.

## Run Locally

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

## Endpoints

- `GET /health`: service health.
- `POST /analyze`: combines URL, DOM, threat intel, TLS, and optional ML signals.
- `POST /report`: receives false positive or false negative feedback and persists host-level label metadata in SQLite.
- `GET /diagnostics`: development counters without URLs or page content.

## Development Controls

- `PHISHLENS_ENABLE_DIAGNOSTICS`: enables `/diagnostics`.
- `PHISHLENS_ENABLE_RATE_LIMITING`: enables in-memory rate limits for `/analyze` and `/report`.
- `PHISHLENS_BEHIND_PROXY`: trusts `X-Forwarded-For` for rate limiting when deployed behind a trusted reverse proxy.
- `PHISHLENS_FEEDBACK_DB_PATH`: SQLite path for persisted feedback metadata. Set to an empty string to disable persistence.
- `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE`: enables localhost-only demo scoring for the local walkthrough.

## Privacy Boundary

The API expects only a URL and structured DOM features. Do not send HTML, credentials, form values, cookies, tokens, or private user content.
