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
- `POST /report`: receives false positive or false negative feedback without persistence.

## Privacy Boundary

The API expects only a URL and structured DOM features. Do not send HTML, credentials, form values, cookies, tokens, or private user content.
