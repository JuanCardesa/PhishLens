# Changelog

## Unreleased

### Extension

- **Proactive badge updates**: Content script sends `PHISHLENS_PAGE_READY` on page load; service worker runs local scoring and sets the action badge colour immediately, without the user needing to open the popup. No new Chrome permissions required.
- **SHA-256 cache key**: Replaced the 32-bit polynomial hash used for `chrome.storage.local` cache keys with a SHA-256-derived 16-character hex prefix (`crypto.subtle.digest`), eliminating trivial key collisions.
- **Expired cache eviction on read**: Cached analysis entries older than 5 minutes are removed from storage when read, preventing stale results from being served after the TTL window.
- **Retry logic on network errors**: `requestBackendAnalysis` retries once (200 ms delay) on transient network errors. AbortError (timeout) and non-2xx HTTP responses are not retried.
- **`npm ci` in CI**: Extension CI now uses `npm ci` instead of `npm install` for reproducible lockfile-based installs.
- **Options dark mode**: Added a system-preference-aware dark mode toggle in the Options page.
- **Structured risk breakdown**: Popup displays a per-category score breakdown (URL, DOM, threat intel, TLS, ML) sourced from `risk_breakdown` in the analysis response.

### Backend

- **Health check with real dependency probes**: `GET /health` now runs `FEEDBACK_STORE.count()` and `is_model_available()`; returns `503` when the feedback store is unavailable. ML absence does not affect the status code.
- **`TTLCache` max-size with LRU-style eviction**: `TTLCache` accepts a `max_size` parameter (default 1000). When at capacity (after expired entry pruning), the soonest-to-expire entry is evicted. Updating an existing key never triggers eviction.
- **ML model SHA-256 audit log**: On first load, `ml_service` computes a SHA-256 digest of the model file bytes and logs the first 16 hex characters at `INFO` level for integrity traceability.
- **Strict mypy CI**: Backend CI runs `mypy --strict` on every push via a dedicated `mypy.ini` configuration.
- **PR Guardian**: `scripts/ci/pr_guardian.py` enforces the allowed Chrome permissions set (`activeTab`, `scripting`, `storage`) and fails CI if `manifest.json` requests anything outside that list.
- **Multi-stage Docker build**: Dockerfile uses a builder stage for dependency installation and a lean runtime stage; `docker-compose.yml` hardened with `read_only`, `no-new-privileges`, and dropped Linux capabilities.
- **SSRF guard documented**: Accepted risk of DNS-based SSRF (bypassing IP-literal blocking) documented in `docs/threat-model.md` with rationale and recommended network-level mitigation.
- **`.env.example` restored**: `PHISHLENS_DIAGNOSTICS_TOKEN` and inline comments for proxy/demo flags were missing from a prior merge; restored with full annotation.

### Tests

- **Extension test coverage**: Added unit tests for `cacheKey` (4 cases), retry behaviour in `requestBackendAnalysis` (3 cases), and `collectDomFeatures`/`hasExternalAction` helpers.
- **Backend test coverage**: Added tests for `TTLCache` max-size eviction, health endpoint 503 degraded state, and `FeedbackStore.count()` monkeypatching.
- **Chrome mock hardened**: `setup.ts` adds `chrome.runtime.sendMessage` and `chrome.runtime.onMessage.addListener` to the top-level and per-test stubs.

### Documentation

- **README**: Added screenshots section, Linux/macOS setup commands, corrected demo URLs (`localhost` not `127.0.0.1`), and noted `/docs` FastAPI interactive explorer.
- **Threat model**: Added SSRF-via-DNS entry to the risks list and a full "Accepted Risks And Limitations" section.

## v0.2.0

- Added reproducible local safe, suspicious, and dangerous demo pages.
- Added backend request IDs, diagnostics counters, sanitized validation responses, and in-memory rate limiting.
- Added explicit localhost-only demo threat source guarded by `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE`.
- Improved popup status clarity for backend-enriched, local-only, cached, and backend-unavailable modes.
- Added privacy-preserving report copy from the extension popup.
- Added `npm run package` to generate a loadable Chrome extension zip.
- Updated CI to validate demo linting and extension packaging.
- Expanded README, architecture, privacy, demo, roadmap, and release-process documentation.

## v0.1.0

- Initial public release with Chrome MV3 extension, FastAPI backend, hybrid scoring, demo ML pipeline, Docker, CI, and core documentation.
