# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- **Brand-impersonation DOM signals**: the content script (`dom-analyzer.ts`) now flags `brand_text_mismatch` (the page's visible title, `og:site_name`, or first `<h1>` names a known brand — reusing the same curated `KNOWN_BRAND_DOMAINS` list as typosquat detection — whose registrable domain doesn't match the current page) and `favicon_hotlinked_brand` (the favicon `<link>` points at a different origin that is itself a known brand domain, a common phishing-kit laziness pattern). Both are zero-network and require no new permission: no favicon bytes are fetched or hashed. Scored as +12 and +8 respectively within the existing `dom` risk category (cap 30), mirrored in `risk-score.ts` and `scoring_service.py`. This catches cloned login pages hosted on domains with no lexical resemblance to the impersonated brand (e.g. a throwaway `.tk` domain), which typosquat detection — which only compares the domain string — would miss. Limitation: coverage is bounded by the same small curated brand list used for typosquat detection, and there is no image/logo-based visual detection.
- **RDAP domain-age signal**: new `domain_age` risk category (cap 20) backed by `backend/app/services/domain_age_service.py`, querying the free `rdap.org` bootstrap service (no API key, no SSRF exposure to the analyzed host since it always targets `rdap.org`). Domains registered in the last 30/180 days add risk score; missing or privacy-protected registration data scores 0. Cached 24h on success, 30s on transient error, same pattern as `tls_service.py`/`phishtank_service.py`. Wired through backend schemas, `scoring_service.py`, `/diagnostics` capabilities, and the extension's risk breakdown, signal grouping, and Options capability grid.
- **ML model warm-up at startup**: `ml_service.warm_up_model()` is now called from a FastAPI `lifespan` handler in `main.py`. Unpickling the scikit-learn estimator triggers a one-time, multi-second lazy import of sklearn's compiled submodules; previously this cost landed on whichever user request happened to be first (observed: ~5.5s, exceeding the extension's 2.5s default timeout and causing a spurious "Backend unavailable" fallback) and blocked the event loop for concurrent requests. First `/analyze` call after startup dropped from ~5.5s to ~1.4s.
- **Heuristic engine backtest**: `ml/evaluate_heuristics.py` backtests `_score_url`'s point weights against the real dataset (numeric features only — typosquat/homograph can't be backtested without raw domains, which the dataset deliberately doesn't store). Result documented in `docs/ml-methodology.md`: typosquat/homograph detection carries most of the URL category's weight; no weights changed based on this baseline.
- **Per-prediction ML explainability**: `ml_service.py` now builds a `shap.TreeExplainer` once alongside the cached model and computes per-prediction SHAP values at inference time, surfacing the top 2 contributing features as `MLResult.top_factors`. Surfaced as a `"Top ML factors: ..."` reason in the `ml` risk-breakdown category whenever the ML adjustment is non-zero. This is genuinely per-instance (two URLs that both raise risk can cite different top factors), not just the model's global `feature_importances_`. Best-effort: falls back to no explanation if SHAP can't explain the loaded model type, without affecting the prediction itself.
- **Temporal validation**: `ml/evaluate_temporal_drift.py` trains on PhishTank URLs submitted more than 2 years ago and tests on URLs submitted in the last 14 days (using the dump's `submission_time` field), with a disjoint Tranco rank window for legitimate URLs. Result: 0.91 accuracy, within noise of the random-split CV/hold-out numbers — the model generalizes to phishing campaigns well outside its training window, not just memorizing snapshot-specific quirks. Documented in `docs/ml-methodology.md` along with the explicit limitation that Tranco has no time axis (only the phishing side is genuinely temporal).

### Fixed

- **ML dataset url-length bias**: legitimate URLs (Tranco roots) and phishing URLs (PhishTank, real paths) were nearly perfectly separable by `url_length` alone, letting the model learn "has a path" instead of phishing patterns. `build_dataset.py` now appends realistic paths to ~80% of legitimate URLs; CV accuracy dropped from an inflated 0.954 to a more honest 0.907. Regression test added in `test_ml_dataset_builder.py`.
- **Local-only "dangerous" label unreachable**: the extension's offline fallback scorer used a special threshold (60, not 70) because its raw max (65) was below the backend's. `risk-score.ts` now scales the local score onto the same 0-100 range before applying the backend's thresholds, so "dangerous" is reachable without backend enrichment.

- **IDN scoring canonicalization**: backend URL normalization now converts Unicode hostnames to IDNA ASCII to match the extension fallback, while punycode markers and punycode-internal hyphens are treated as representation details rather than standalone risk signals.
- **Typosquatting and combosquatting detection**: `feature_extractor.py` (backend) and `url-features.ts` (extension) now compare the registrable label against a curated list of frequently-impersonated brand domains using Levenshtein distance (catches near-misses like `paypa1.com` and `paypa1.net`) and hyphen-delimited combo matching (catches combosquats like `paypal-secure-login.com`). A match adds 14 URL risk points and surfaces a `"Domain closely resembles <brand> (possible typosquatting)"` reason. Mirrored identically between backend and extension fallback scoring, with parity tests in both `test_scoring_parity.py` and `risk-score.test.ts`.
- **Unicode homograph detection**: replaces the previous punycode-presence-only signal with real IDN spoofing detection. Each registrable label is IDNA-decoded (a self-contained RFC 3492 punycode decoder in the extension, `label.encode("ascii").decode("idna")` in the backend — no new dependencies) and run through a confusable-character table (Cyrillic/Greek look-alikes, e.g. Cyrillic "а" → "a") before the existing typosquat comparison, so full-script spoofs like the classic `xn--80ak6aa92e.com` ("аррӏе.com") now match `apple.com` at distance 0 and score +16 with a `"...look-alike Unicode characters... (homograph attack)"` reason. A second, independent signal flags any label mixing two or more Unicode scripts (e.g. Latin + Cyrillic in `gооgle.com`) for +8, even when it doesn't match a known brand. Mirrored between `feature_extractor.py` and `url-features.ts` with parity tests.
- **Real ML training dataset**: `ml/datasets/real_phishing_urls.csv` (1200 rows: 600 verified PhishTank phishing URLs + 600 Tranco top-50k legitimate domains) is now built and committed — the model previously shipped was trained on the 13-row synthetic demo set despite `ml-methodology.md` describing a real-dataset pipeline. The CSV holds only the 16 numeric features and a label, never raw URLs, so it carries no privacy risk. Retrained model (`v0.3.0-real`): 0.954 ± 0.009 stratified 5-fold CV accuracy, 0.95 hold-out accuracy. `ml/datasets/build_dataset.py` fixed to use the current Tranco download endpoint (the old `latest/full` alias was retired; the list is now a zip), HTTPS for the PhishTank dump, and the backend URL feature extractor to avoid training/inference skew. `ml/evaluate_model.py` now validates the saved artifact's dataset metadata, and the backend runtime artifact is packaged at `backend/app/models/phishlens_model.joblib`.

---

## [0.3.0] — 2026-06-22 — stabilization, security hardening, and portfolio polish

### Added

- **SSRF protection**: `url_normalizer.py` now blocks private and loopback IP literals (`127.x`, `10.x`, `192.168.x`, `::1`, link-local, etc.) using Python's `ipaddress` module. Hostnames that _resolve_ to private addresses remain an accepted risk (DNS-based SSRF), documented in `docs/threat-model.md`.
- **Private-IP SSRF tests**: parametrized `pytest` cases cover IPv4 loopback, RFC-1918 ranges, IPv6 loopback, link-local, and a public IP allow-case.
- **`isAnalysisResponse` runtime guard**: `analysis-api.ts` validates the `/analyze` response shape before casting — malformed backend payloads now return `null` instead of silently propagating an invalid object.
- **Port/protocol origin check for form actions**: `hasExternalAction` in `dom-analyzer.ts` now compares the full origin (`scheme + host + port`) instead of hostname only. A form targeting `http://site.com:9999` from an `https://site.com` page is now correctly flagged as cross-origin.
- **`SECURITY.md`**: vulnerability disclosure policy with scope, reporting contact, and a summary of the accepted risks already documented in `docs/threat-model.md`.
- **`.github/CODEOWNERS`**: default repository ownership.
- **Test coverage reporting**: `pytest-cov` (backend) and `vitest --coverage` (extension) wired into CI, uploaded to Codecov (`codecov/codecov-action@v5`) with a badge in the README. Backend coverage: 87%. Extension coverage: 82% (up from 59% after adding `@testing-library/react` render tests for `Popup.tsx` and `Options.tsx`).
- **`backend/tests/test_scoring_service.py`**: regression tests for the mutually-exclusive TLS scoring fix below.
- **`extension/src/popup/Popup.render.test.tsx` and `extension/src/options/Options.render.test.tsx`**: component-level tests covering loading states, backend-enriched/unavailable modes, feedback submission, and settings save/refresh flows.
- Repository metadata: GitHub topics and homepage URL set to the project site.

### Changed

- **PhishTank transport**: `PHISHTANK_CHECK_URL` switched from `http://` to `https://`. API key and URL are no longer transmitted in cleartext.
- **TLS scoring**: restructured to be mutually exclusive — an expired certificate now emits one reason ("appears to be expired", 15 pts) instead of two ("could not be validated" + "expired", 25 pts before cap). Order: expired → nearly expired → invalid → error.
- **Local `dangerous` threshold**: lowered from 70 to 60 in `risk-score.ts`. The local scorer's maximum is `URL_SCORE_CAP(35) + DOM_SCORE_CAP(30) = 65`, making 70 permanently unreachable without backend enrichment. The new threshold makes `dangerous` achievable in local-only mode.
- **URL fragment normalisation**: `analyzeLocally()` strips the URL fragment before extracting features, matching the backend's `normalize_url` behaviour and preventing divergent scores for the same page.
- **Cache privacy**: `writeCachedAnalysis` now strips the query string and fragment from the `url` field stored in `chrome.storage.local`. The cache key (SHA-256 of the full URL) is unchanged; only the persisted value is sanitised.
- **ML dataset row check**: `train_model.py` now applies separate thresholds — ≥ 100 rows for the real dataset, ≥ 4 rows for the synthetic demo. The previous flat `< 20` check broke the included 12-row demo CSV.
- **`dom-analyzer.ts` content script**: top-level `await chrome.runtime.sendMessage(…)` wrapped in an async IIFE. MV3 content scripts are classic scripts (not ES modules) and cannot use top-level `await`.
- **`PHISHLENS_MODEL_PATH` default**: `.env.example` corrected from `../ml/models/…` (relative to `backend/`) to `ml/models/…` (relative to the repo root where `uvicorn` is invoked).

### Fixed

- **`chrome-web-store.md`**: corrected privacy disclosure — feedback _is_ persisted in SQLite (hostname, label, note presence, request ID, timestamp), not "not durably stored".
- **Dead imports** in `ml/datasets/build_dataset.py`: removed unused `re` and `unicodedata` imports that caused `ruff F401` failures.
- **`pr_guardian.py`**: the sensitive-surface-docs check only recognized `.test.ts` as a test-only file, not `.test.tsx` — the first JSX test files in the repo were incorrectly flagged as undocumented sensitive-surface changes.

---

## [0.2.2] — portfolio hardening

### Added

- **CI badges** in README linking to backend, extension, and security workflows on GitHub Actions.
- **Quick Start** section in README: five commands to get the project running locally.
- **Environment variables table** in README with default values and descriptions for all `PHISHLENS_*` settings.
- **`CONTRIBUTING.md`**: setup, test commands, commit conventions, and PR checklist.
- **`diagnostics_token` auth**: `GET /diagnostics` now checks `X-Diagnostics-Token` header when `PHISHLENS_DIAGNOSTICS_TOKEN` is set; returns `401` on mismatch. Closes the gap between `.env.example` documentation and actual enforcement.
- **JSON structured logging**: `app/core/logging_config.py` configures the root logger with a stdlib JSON formatter. Every log record emits `timestamp`, `level`, `logger`, `message`, and any extra fields (e.g. `request_id`, `method`, `path`, `status_code`, `duration_ms`).
- **React Error Boundary**: `ErrorBoundary.tsx` wraps the popup root. Unhandled render errors show a user-facing fallback with a "Try again" button instead of a blank popup.
- **`content_security_policy`** field added to `manifest.json` (`script-src 'self'; object-src 'none'`), making the MV3 default explicit and auditable. CSP meta tags added to `popup.html` and `options.html` for tooling visibility.
- **`Options.test.ts`**: unit tests for `diagnosticsLabelFor()` covering all `BackendStatus` states.
- **`ml/datasets/build_dataset.py`**: downloads PhishTank verified phishing URLs and Tranco top-1M legitimate domains, extracts URL features, and writes `real_phishing_urls.csv` (~1 200 balanced rows). DOM features are 0 for all rows (browser context required).
- **ML methodology docs**: `docs/ml-methodology.md` updated with dataset sources table, build instructions, and metrics guidance.
- **GitHub Pages link** added to README header.
- **Link to `docs/ml-methodology.md`** added to README.

### Changed

- **`requestBackendAnalysis` retry logic**: 5xx responses (transient server errors) now fall through to the retry loop. 4xx responses (429, 422, etc.) still return `null` immediately. Previously, all non-2xx responses skipped retry.
- **`isDOMFeatures` type guard**: `collectDomFeatures()` in `Popup.tsx` now validates the content script response shape before casting, falling back to `EMPTY_DOM_FEATURES` on unexpected payloads.
- **`train_model.py`** auto-detects `real_phishing_urls.csv` and falls back to the synthetic demo set; version string updates accordingly (`0.3.0-real` / `0.2.0-synthetic`).
- **`docs/permissions.md`** updated to document the new `content_security_policy` manifest field.
- **Configuration section** in README reformatted from bullet list to a table with default values.

### Fixed

- **`FeedbackStore.count()` race condition**: method now acquires `self._lock` before executing the `SELECT COUNT(*)` query, consistent with `record()`.
- **`docker-compose.yml`** now includes `security_opt: [no-new-privileges:true]`, `read_only: true`, `cap_drop: [ALL]`, and a `tmpfs` mount for `/tmp`. Previously the CHANGELOG documented this hardening but the compose file did not reflect it.
- **30-day feedback retention**: `_init_schema()` runs `DELETE FROM feedback WHERE created_at < datetime('now', '-30 days')` on store startup.
- **Dead `_now_utc()` removed** from `feedback_store.py` (was already unused after a prior refactor).

### Security

- Diagnostics endpoint now enforces token authentication when `PHISHLENS_DIAGNOSTICS_TOKEN` is configured.
- Docker container now runs with a read-only root filesystem and no Linux capabilities.
- Extension pages now declare explicit CSP in `manifest.json`.

---

## [0.2.1] — review fixes

### Added

- Proactive badge updates via `PHISHLENS_PAGE_READY` from content script.
- SHA-256 cache key for `chrome.storage.local` (replaced 32-bit polynomial hash).
- Expired cache eviction on read (5-minute TTL enforced at read time).
- Retry logic on transient network errors in `requestBackendAnalysis`.
- Health check with real dependency probes (`FEEDBACK_STORE.count()`, `is_model_available()`); returns `503` when feedback store is unavailable.
- `TTLCache` max-size with LRU-style eviction.
- ML model SHA-256 audit log on first load.
- PR Guardian script enforcing Chrome permission allowlist, secret scanning, and scoring test coupling.
- SSRF guard: accepted risk of DNS-based SSRF documented in `docs/threat-model.md`.

### Changed

- Extension CI uses `npm ci` for reproducible installs.
- Options page gained system-preference-aware dark mode.
- Structured risk breakdown (URL / DOM / threat intel / TLS / ML) sourced from `risk_breakdown` field.
- Strict `mypy --strict` added to backend CI.

### Fixed

- Multi-stage Docker build: lean runtime image with no pip, git, or compiler.
- `.env.example` restored with `PHISHLENS_DIAGNOSTICS_TOKEN` and inline comments.

---

## [0.2.0]

- Added reproducible local safe, suspicious, and dangerous demo pages.
- Added backend request IDs, diagnostics counters, sanitized validation responses, and in-memory rate limiting.
- Added explicit localhost-only demo threat source guarded by `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE`.
- Improved popup status clarity for backend-enriched, local-only, cached, and backend-unavailable modes.
- Added privacy-preserving report copy from the extension popup.
- Added `npm run package` to generate a loadable Chrome extension zip.
- Updated CI to validate demo linting and extension packaging.
- Expanded README, architecture, privacy, demo, roadmap, and release-process documentation.

## [0.1.0]

- Initial public release with Chrome MV3 extension, FastAPI backend, hybrid scoring, demo ML pipeline, Docker, CI, and core documentation.
