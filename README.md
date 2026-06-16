# PhishLens

PhishLens is a defensive Chrome extension and FastAPI backend for explainable phishing risk analysis in real time.

It combines local URL heuristics, privacy-preserving DOM signals, optional PhishTank threat intelligence, backend-side TLS certificate inspection, and an optional machine learning model. The project is built as a practical cybersecurity portfolio project with clear safety boundaries.

## Current Status

Sprint 3 demo and release readiness implemented:

- Chrome Extension Manifest V3 with React popup.
- Local URL and DOM heuristic analysis.
- Options page for backend URL, timeout, and dangerous overlay settings.
- User feedback reporting from the popup to `/report`.
- Informative, dismissible overlay for `dangerous` results.
- FastAPI backend with `/health`, `/analyze`, and `/report`.
- PhishTank integration prepared through environment variables.
- TLS inspection implemented in the backend.
- URL normalization and in-memory TTL cache for PhishTank and TLS checks.
- Demo ML training and evaluation pipeline.
- Docker Compose and GitHub Actions workflows.
- Privacy, threat model, architecture, ML methodology, and roadmap docs.
- Reproducible local demo pages.
- Development diagnostics with request IDs and no sensitive payloads.
- In-memory rate limiting for analysis and feedback endpoints.
- Extension release packaging script.

## Architecture

```text
Chrome page
  -> content script extracts non-sensitive DOM signals
  -> popup computes local heuristic score
  -> popup optionally calls FastAPI /analyze
  -> backend adds URL, threat intel, TLS, and ML signals
  -> popup shows score, label, confidence, reasons, and feedback controls
  -> dangerous results can display a dismissible page overlay
  -> development diagnostics expose counters only
```

The extension never sends full HTML, form values, passwords, or typed emails. The backend receives only the current URL and technical DOM features.

## Stack

- Extension: TypeScript, React, Vite, Chrome Extension API, Manifest V3.
- Backend: Python, FastAPI, Pydantic, httpx, scikit-learn, pandas, joblib.
- Quality: pytest, ruff, TypeScript checks, GitHub Actions.
- Runtime: Docker and Docker Compose.

## Development Setup

### Backend

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

### Extension

```bash
cd extension
npm install
npm run build
```

Load `extension/dist` in Chrome:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Select "Load unpacked".
4. Choose the `extension/dist` folder.

The extension works locally without the backend. When the backend is available at `http://localhost:8000`, the popup enriches the local result with backend analysis.

Extension settings are available from the popup settings button or Chrome extension details page. The default backend is `http://localhost:8000`.

## Tests

Backend:

```bash
pytest backend/tests
```

Extension:

```bash
cd extension
npm run lint
npm run test
npm run build
npm audit --audit-level=high
```

ML demo:

```bash
python ml/train_model.py
python ml/evaluate_model.py
```

Docker:

```bash
docker compose build
docker compose up backend
```

## Configuration

Copy `.env.example` to `.env` for local overrides.

- `PHISHTANK_API_KEY`: optional PhishTank application key.
- `PHISHTANK_USER_AGENT`: descriptive User-Agent required by PhishTank.
- `PHISHLENS_ALLOWED_ORIGINS`: backend CORS origins. Add `chrome-extension://*` (or a specific extension origin) only when extension access is required.
- `PHISHLENS_ENABLE_THREAT_INTEL`: enable or disable threat intel checks.
- `PHISHLENS_ENABLE_TLS_ANALYSIS`: enable or disable backend TLS checks.
- `PHISHLENS_MODEL_PATH`: optional path to a trained joblib model.
- `PHISHLENS_ENABLE_DIAGNOSTICS`: enable development diagnostics.
- `PHISHLENS_ENABLE_RATE_LIMITING`: enable in-memory rate limits.
- `PHISHLENS_ANALYZE_RATE_LIMIT`: per-window `/analyze` request limit.
- `PHISHLENS_REPORT_RATE_LIMIT`: per-window `/report` request limit.
- `PHISHLENS_RATE_LIMIT_WINDOW_SECONDS`: rate-limit window.
- `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE`: localhost-only dangerous demo signal.

No real keys are committed.

Extension settings:

- Backend URL: defaults to `http://localhost:8000`.
- Timeout: clamped between 1000 ms and 10000 ms.
- Danger overlay: enabled by default and only shown for `dangerous` results.

## Ethical And Privacy Notice

PhishLens is defensive only. It must not collect credentials, typed emails, private form content, or full page HTML. It is a risk-assistance tool, not a phishing verdict authority. False positives and false negatives are expected, especially before training on a real dataset.

## Local Demo

Run the backend, demo pages, and extension locally:

```bash
$env:PHISHLENS_ENABLE_DEMO_THREAT_SOURCE="true"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
python demo/serve_demo.py
cd extension
npm run build
```

Load `extension/dist` in Chrome and visit:

- `http://127.0.0.1:8080/pages/safe.html`
- `http://127.0.0.1:8080/pages/suspicious.html`
- `http://127.0.0.1:8080/pages/phishlens-demo-dangerous-login-secure-update.html`

The dangerous demo requires `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true` and only matches localhost/127.0.0.1 URLs containing `phishlens-demo-dangerous`.

Package the extension:

```bash
cd extension
npm run package
```

The zip is written to `extension/release/`.

## Limitations

- The included ML dataset is synthetic demo data only.
- TLS analysis runs from the backend and may differ from what the browser sees behind proxies or TLS inspection.
- PhishTank checks require a user-provided API key and are rate limited.
- Feedback is logged for review only; durable storage is intentionally deferred.
- Diagnostics are development counters only and should not be treated as production telemetry.
- In-memory rate limiting is process-local and resets when the backend restarts.
- The current build prioritizes explainability and safe defaults over coverage.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).
