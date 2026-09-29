# PhishLens

[![Backend CI](https://github.com/JuanCardesa/PhishLens/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/JuanCardesa/PhishLens/actions/workflows/backend-ci.yml)
[![Extension CI](https://github.com/JuanCardesa/PhishLens/actions/workflows/extension-ci.yml/badge.svg)](https://github.com/JuanCardesa/PhishLens/actions/workflows/extension-ci.yml)
[![Security CI](https://github.com/JuanCardesa/PhishLens/actions/workflows/security-ci.yml/badge.svg)](https://github.com/JuanCardesa/PhishLens/actions/workflows/security-ci.yml)
[![codecov](https://codecov.io/gh/JuanCardesa/PhishLens/branch/main/graph/badge.svg)](https://codecov.io/gh/JuanCardesa/PhishLens)

**[Project site](https://juancardesa.github.io/PhishLens/)** · [Architecture](docs/architecture.md) · [Privacy policy](docs/privacy.md) · [Threat model](docs/threat-model.md) · [ML methodology](docs/ml-methodology.md) · [Demo script](docs/demo-script.md)

PhishLens is a defensive Chrome extension and FastAPI backend for explainable phishing risk analysis in real time.

It combines local URL heuristics, privacy-preserving DOM signals, optional PhishTank threat intelligence, backend-side TLS certificate inspection with Certificate Transparency lookups, RDAP domain-age checks, and an optional machine learning model. The project is built as a practical cybersecurity portfolio project with clear safety boundaries.

![PhishLens on a cloned PayPal login at paypal-verify-account.net: the toolbar icon shows a red badge, the popup rates the page Dangerous 74/100 with backend enrichment, and the in-page warning lists the reasons and tells the user not to enter a password](docs/screenshots/hero-phishing-detection.png)

_PhishLens flagging a cloned PayPal login on a look-alike domain (`paypal-verify-account.net`) and explaining why, both in the popup and in the in-page warning. Captured from the recording below; both sites are local demo pages and the domain is not registered. End-to-end walkthrough, from a phishing email to the in-page warning:_

![PhishLens end-to-end demo: a fake "PayPal Security" email links to a cloned login on paypal-verify-account.net, the PhishLens toolbar icon turns red, the popup rates the page Dangerous 74/100 with a per-category breakdown (URL 32/35, page structure 30/30, ML +12), and a warning overlay covers the page](docs/screenshots/demo.webp)

## Quick Start

```bash
# 1. Clone and set up the backend
git clone https://github.com/JuanCardesa/PhishLens.git && cd PhishLens
cp .env.example .env
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt

# 2. Start the backend
uvicorn app.main:app --app-dir backend --reload

# 3. Build the extension
cd extension && npm install && npm run build

# 4. Load the extension in Chrome: chrome://extensions → Developer mode → Load unpacked → select extension/dist

# 5. (Optional) Build a real ML dataset and retrain the model
python ml/datasets/build_dataset.py && python ml/train_model.py
```

## Current Status

- **Detection.** URL heuristics (typosquatting via Levenshtein, homograph/IDN attacks via a hand-written punycode decoder and confusable map, a brand's full domain hidden in subdomains) and privacy-preserving DOM signals (credential fields, external form actions, brand impersonation), scored into an explainable risk breakdown by URL, DOM, threat intelligence, TLS, domain age, and ML.
- **Backend enrichment (FastAPI).** `/analyze`, `/report`, `/health`; PhishTank threat intel, backend TLS + Certificate Transparency inspection, RDAP domain-age lookups — each with URL normalization, TTL caching, timeouts, and clean degradation when unavailable.
- **Extension (MV3).** A toolbar badge scored locally as each page loads, a React popup with a risk breakdown and feedback controls, an options page (backend URL, timeout, overlay), and a dismissible warning overlay for `dangerous` results. Works fully offline; the backend only enriches. Firefox support is experimental: the code and manifest are cross-browser, but it has not been click-tested in a real Firefox profile.
- **ML.** Training and evaluation pipeline on a real PhishTank + Tranco dataset, with SHAP per-prediction explanations and documented limitations (see [ML methodology](docs/ml-methodology.md)).
- **Quality & safety.** Unit tests plus a shared ext/backend scoring contract and a real-Chromium E2E smoke test; rate limiting, structured diagnostics with no sensitive payloads, host-only SQLite feedback, Docker, and CI (backend, extension, security, PR Guardian).

## Screenshots

The popup on the local demo pages (`demo/pages/`), captured with `extension/scripts/record-demo.mjs`.

| Safe page (backend-enriched) | Dangerous page (backend-enriched) | Local-only mode (no backend response) |
|---|---|---|
| ![Safe demo page: Safe 5, backend enriched, the only URL signal is the lack of HTTPS](docs/screenshots/popup-safe.png) | ![Dangerous demo page: Dangerous 94, backend enriched, with URL and page-structure signals and the demo threat source](docs/screenshots/popup-dangerous.png) | ![Safe demo page without a backend response: Safe 8, confidence shown as "Heuristic" instead of a percentage, backend marked Local only](docs/screenshots/popup-local-only.png) |

The warning overlay on the dangerous demo page. That page also matches the localhost-only demo threat source (see [Local Demo](#local-demo)):

![Danger overlay: "High-risk phishing signals detected", risk score 94/100, the top reasons, and a Continue button](docs/screenshots/danger-overlay.png)

## Architecture

```text
Chrome page
  -> content script extracts non-sensitive DOM signals
  -> service worker scores the page locally and sets the toolbar badge
  -> popup computes local heuristic score
  -> popup optionally calls FastAPI /analyze
  -> backend adds URL, threat intel, TLS + Certificate Transparency, domain age, and ML signals
  -> popup shows score, label, confidence, risk breakdown, and feedback controls
     (confidence is a percentage only when the ML model contributed, "Heuristic" otherwise)
  -> dangerous results can display a dismissible page overlay
  -> development diagnostics expose counters only
```

The extension never sends full HTML, form values, passwords, or typed emails. The backend receives only the current URL and technical DOM features.

## Stack

- Extension: TypeScript, React, Vite, Manifest V3, `webextension-polyfill` (for the experimental Firefox build).
- Backend: Python, FastAPI, Pydantic, httpx, scikit-learn, SHAP, pandas, joblib.
- Quality: pytest, ruff, mypy, Vitest, TypeScript checks, Playwright (real-Chromium E2E), GitHub Actions, Codecov.
- Runtime: Docker and Docker Compose.

## Development Setup

### Backend

**Linux / macOS**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
uvicorn app.main:app --app-dir backend --reload
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Interactive API documentation is available at `http://localhost:8000/docs` while the backend is running.

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

Backend (the same checks as Backend CI):

```bash
cd backend
pytest tests
ruff check app tests ../demo
mypy app
```

Extension (the same checks as Extension CI):

```bash
cd extension
npm run lint                        # tsc --noEmit
npm run test
npm run build
npx playwright install chromium     # first run only
npm run test:e2e                    # loads the built extension in real Chromium
```

Dependency audits (run by Security CI, not Extension CI):

```bash
cd extension && npm audit --audit-level=high
pip install pip-audit && pip-audit -r backend/requirements.txt
```

ML:

```bash
python ml/train_model.py
python ml/evaluate_model.py
python ml/evaluate_cv_metrics.py    # the metrics in "ML model performance" below
```

Docker:

```bash
docker compose build
docker compose up backend
```

Review automation:

```bash
python scripts/ci/pr_guardian.py --all
```

Demo readiness:

```bash
python scripts/dev/check_demo.py
```

## Configuration

Copy `.env.example` to `.env` for local overrides. No real keys are committed.

| Variable | Default | Description |
|----------|---------|-------------|
| `PHISHTANK_API_KEY` | _(empty)_ | Optional PhishTank application key. Omit to skip threat intel. |
| `PHISHTANK_USER_AGENT` | `phishtank/phishlens-demo` | User-Agent sent with PhishTank requests (required by their API). |
| `PHISHLENS_ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins. Add `chrome-extension://*` only for local dev. |
| `PHISHLENS_CHROME_EXTENSION_IDS` | _(empty)_ | Comma-separated Chrome extension IDs for production CORS. |
| `PHISHLENS_ENABLE_THREAT_INTEL` | `true` | Enable/disable PhishTank lookups. |
| `PHISHLENS_ENABLE_TLS_ANALYSIS` | `true` | Enable/disable backend TLS certificate inspection. |
| `PHISHLENS_ENABLE_CT_LOG_LOOKUP` | `true` | Enable/disable Certificate Transparency log lookups (crt.sh) as an additional TLS risk signal. |
| `PHISHLENS_ENABLE_DOMAIN_AGE_LOOKUP` | `true` | Enable/disable RDAP domain-registration-age lookups. |
| `PHISHLENS_EXTERNAL_TIMEOUT_SECONDS` | `4.0` | Timeout for external backend enrichment calls such as PhishTank, RDAP, and crt.sh. |
| `PHISHLENS_MODEL_PATH` | `app/models/phishlens_model.joblib` | Path to a trained joblib model artifact. |
| `PHISHLENS_BRAND_DOMAINS_PATH` | `app/data/brand_domains.json` | Path to the curated brand-domain list used for typosquat/brand-impersonation detection. |
| `PHISHLENS_ENABLE_DIAGNOSTICS` | `true` | Expose aggregate counters at `GET /diagnostics`. |
| `PHISHLENS_DIAGNOSTICS_TOKEN` | _(empty)_ | When set, `GET /diagnostics` requires `X-Diagnostics-Token: <value>`. |
| `PHISHLENS_ENABLE_RATE_LIMITING` | `true` | Enable in-memory sliding-window rate limits. |
| `PHISHLENS_ANALYZE_RATE_LIMIT` | `60` | Max `/analyze` requests per window per IP. |
| `PHISHLENS_REPORT_RATE_LIMIT` | `20` | Max `/report` requests per window per IP. |
| `PHISHLENS_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window in seconds. |
| `PHISHLENS_BEHIND_PROXY` | `false` | Trust `X-Forwarded-For` when behind nginx / Caddy / ALB. |
| `PHISHLENS_FEEDBACK_DB_PATH` | `feedback.db` | SQLite path for feedback metadata. Set to `""` to disable. |
| `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE` | `false` | Enable localhost-only dangerous demo signal. |

Extension settings:

- Backend URL: defaults to `http://localhost:8000`.
- Timeout: defaults to 2500 ms, clamped between 1000 ms and 10000 ms.
- Danger overlay: enabled by default and only shown for `dangerous` results.

## Ethical And Privacy Notice

PhishLens is defensive only. It must not collect credentials, typed emails, private form content, or full page HTML. It is a risk-assistance tool, not a phishing verdict authority. False positives and false negatives are expected, especially outside the limited dataset and signal coverage documented below.

## Local Demo

Run the backend, demo pages, and extension locally, each in its own terminal:

```powershell
# Terminal 1: backend with the localhost-only demo threat source
# (Linux / macOS: PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true uvicorn app.main:app --app-dir backend --reload)
$env:PHISHLENS_ENABLE_DEMO_THREAT_SOURCE="true"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload

# Terminal 2: demo pages on port 8080
python demo/serve_demo.py

# Terminal 3: build the extension
cd extension
npm run build
```

Load `extension/dist` in Chrome and visit:

- `http://localhost:8080/pages/safe.html`
- `http://localhost:8080/pages/suspicious.html`
- `http://localhost:8080/pages/phishlens-demo-dangerous-login-secure-update.html`

The dangerous demo requires `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true` and only matches `localhost` URLs containing `phishlens-demo-dangerous`. Use `localhost` rather than `127.0.0.1`: the backend rejects private IP literals as an SSRF safeguard.

Package the extension:

```bash
cd extension
npm run package
```

The zip is written to `extension/release/`.

## ML model performance

**99.0% precision / 82.2% recall (5-fold stratified CV, N=1,200)** — the two strongest, most
honest metrics for the shipped `RandomForestClassifier` on the committed PhishTank + Tranco
dataset. Accuracy alone (**90.7%**) is a poor headline for a detector: here it hides a recall
gap — the model catches ~82% of phishing at near-perfect precision, so its weakness is *missed*
phishing, not false alarms.

Reproduce with `python ml/evaluate_cv_metrics.py`. Phishing is the positive class; the confusion
matrix and false-positive rate are aggregated out-of-fold across all 5 folds (every row predicted
exactly once).

| Metric | As-is (N=1,200) | Leakage-corrected (N=915) |
|--------|----------------:|--------------------------:|
| Class balance (phishing / legit) | 600 / 600 (50.0%) | 481 / 434 (52.6%) |
| Precision | 0.990 | 0.993 |
| Recall | 0.822 | 0.869 |
| F1 | 0.898 | 0.927 |
| False-positive rate | 0.0083 | 0.0069 |
| ROC-AUC | 0.966 | 0.970 |
| Accuracy | 0.907 | 0.928 |
| Confusion matrix `[[TN, FP], [FN, TP]]` | `[[595, 5], [107, 493]]` | `[[431, 3], [63, 418]]` |

**On class balance:** this dataset is balanced 50/50 by construction, so the usual "accuracy is
misleading because phishing is rare" caveat doesn't apply to *this* evaluation — accuracy is
misleading here for a different reason (it averages over a strong precision and a weaker recall).
In production, phishing is of course rare, which is a further reason to track precision/recall/FPR
rather than accuracy.

**On data leakage:** the committed CSV stores only the 16 numeric features and a label, never raw
URLs or domains (a deliberate privacy decision), so *domain-level* leakage (same host in train and
test) can't be verified from the file. The closest observable proxy is duplicate feature vectors —
439 of the 1,200 rows are exact duplicates (915 distinct vectors), because PhishTank captures many
paths on one host and Tranco roots collapse to identical numeric rows, so a random k-fold split can
place identical vectors in both train and test. The "Leakage-corrected" column removes that vector
by deduplicating to one row per distinct feature vector. Its numbers are *higher*, not lower — so
the duplicates are conservative, not inflationary, and the headline accuracy is **not** propped up
by leakage. Both columns are reported for transparency; treat the as-is column as the conservative
figure.

**These numbers describe a URL-only model, not production behavior.** DOM features
(`has_password_field`, `num_forms`, etc.) are hardcoded to `0` for every training row because the
dataset is built from URLs only, without a live browser session — but
`backend/app/services/ml_service.py` feeds real DOM features from the extension's content script at
inference time. The 6 DOM columns the model sees in production were never exercised with real
variation during training, so any influence they have on live predictions is unvalidated
extrapolation. See [docs/ml-methodology.md](docs/ml-methodology.md) for the full methodology, the
URL-length dataset bias that was found and fixed, and the temporal-drift validation.

## Limitations

- The ML model is trained on a real PhishTank + Tranco dataset (1,200 rows). See
  [ML model performance](#ml-model-performance) above for the full metric table and the caveat that
  these figures describe a URL-only model — the 6 DOM columns it receives in production were never
  exercised with real variation during training.
- TLS analysis runs from the backend and may differ from what the browser sees behind proxies or TLS inspection.
- PhishTank checks require a user-provided API key and are rate limited.
- Feedback storage is intentionally minimal: hostname, labels, note presence, request ID, and timestamp only. It is not a replacement for a reviewed training dataset.
- Diagnostics are development counters only and should not be treated as production telemetry.
- In-memory rate limiting is process-local and resets when the backend restarts.
- Known false positive: the real PayPal sign-in page (`https://www.paypal.com/signin`) scored
  **Suspicious 36** when the demo was recorded. Its genuine login form, password field, reCAPTCHA
  iframes, and hidden inputs raise the page-structure score, and the ML model adds +20 citing the
  number of subdomains and dots, so it effectively penalizes the `www.` prefix.
- The local score and the backend-enriched score are on the same 0-100 scale but can disagree
  noticeably for the same page. On the cloned PayPal login in the demo recording, the popup first
  showed the local-only score (95) and then the backend score (74). The toolbar badge always
  reflects the local label (`!`, `?`, or nothing), never the backend result, so the two can
  disagree.
- The current build prioritizes explainability and safe defaults over coverage.

## Lessons Learned

A few things found during a deliberate self-audit of this project, kept here instead of
quietly fixed and forgotten, because how a bug was found and corrected is often more
informative than the fact that the code is now clean:

- **The content script and danger overlay were silently broken in real Chrome, while every automated check stayed green.** Adding Firefox support introduced an ES `import` statement into two files that execute as classic, non-module scripts (MV3 content scripts and `chrome.scripting.executeScript`-injected files can't be modules). `tsc`, `vitest`, and `vite build` all passed, because none of them load the bundle in an actual browser — Vitest mocks the module graph, and Vite's build doesn't check runtime module-format compatibility. Found by recording this README's original demo GIF with a real Playwright + Chromium session instead of a screen recording tool, which surfaced "Could not establish connection" the moment the popup tried to collect DOM features. Fixed by splitting the build into two Rollup passes — ES modules for popup/options/the service worker, IIFE for the content script and overlay. The lesson: a green test suite proves the code you tested, not the environment you didn't.
- **A 95% ML accuracy number was hiding a trivial shortcut.** The training dataset built
  legitimate URLs as bare domain roots (`https://example.com/`) while phishing URLs from
  PhishTank carry real paths, so `url_length` alone separated the two classes almost
  perfectly — the model was learning "has a path" instead of phishing patterns. Fixed by
  adding realistic paths to legitimate URLs; honest accuracy dropped to ~91% CV. Detailed
  in [docs/ml-methodology.md](docs/ml-methodology.md#known-limitation-found-and-fixed-url-length-separability-bias).
- **The offline fallback's "dangerous" label was effectively unreachable.** It needed
  ~92% of its own maximum possible score because the threshold (60) was hand-picked
  against a smaller scale than the backend's (70) without reconciling the two. Fixed by
  scaling the local score onto the backend's 0-100 range before applying the same
  threshold.
- **Backtesting the URL heuristic weights surfaced their own blind spot.** Without
  typosquat/homograph signals (which need the raw domain — not stored in the dataset for
  privacy), the remaining numeric-only heuristics never reach the scoring cap on this
  dataset. That's not a miscalibration; it confirms typosquat/homograph detection carries
  most of the URL category's weight in practice. See
  [docs/ml-methodology.md](docs/ml-methodology.md#heuristic-engine-backtest-rule-based-scoring-no-ml).
- **A new external call (RDAP) silently exceeded the extension's request timeout.**
  Adding domain-age lookups didn't itself cause this — profiling showed the real cost was
  a one-time, multi-second `sklearn` import triggered by lazily unpickling the ML model on
  the first request, which also blocked the event loop for concurrent requests. Fixed by
  warming up the model from a FastAPI `lifespan` handler at startup; first-request latency
  dropped from ~5.5s to ~1.4s.
- **The heuristic-only "confidence" number is overconfident, not just unproven.** A
  reliability diagram against the committed dataset showed every confidence bin sitting
  below the perfectly-calibrated line, and the bin holding 96% of rows (confidence ≈ 0.90)
  was only ~52% accurate — barely better than guessing. Not "fixed" with a quick correction
  factor in this round, because calibrating against a dataset that can't exercise
  typosquat/homograph/DOM/TLS/domain-age/threat-intel signals would just calibrate to this
  benchmark's blind spots. Instead, the popup stopped presenting it as a probability: when the
  ML model did not contribute, it shows "Heuristic" (with a tooltip explaining why) rather than a
  percentage, and the copied report says "heuristic (not a calibrated probability)". See
  [docs/ml-methodology.md](docs/ml-methodology.md#heuristic-only-confidence-calibration-reliability-diagram).

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).

## Review And Release Process

PhishLens uses deterministic review gates instead of relying on a single reviewer. See [docs/review-methodology.md](docs/review-methodology.md) and [docs/release-process.md](docs/release-process.md).

Publication preparation lives in [docs/chrome-web-store.md](docs/chrome-web-store.md), with permission rationale in [docs/permissions.md](docs/permissions.md).
