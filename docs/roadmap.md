# Roadmap

## 1. Bootstrap

Repository structure, Git flow, docs, CI, Docker, and safe project rules.

## 2. MVP Extension

Manifest V3 extension with popup, local URL scoring, DOM feature collection, and backend fallback behavior.

## 3. Backend FastAPI

Health, analysis, and report endpoints with Pydantic schemas and tests.

## 4. DOM Analyzer

Expand non-sensitive DOM signals while preserving the no-content and no-input-values boundary.

Done: added brand-impersonation detection — a visible-text (title/`og:site_name`/`h1`) brand mismatch against a curated brand-domain list shared with typosquat detection, plus a favicon-hotlinked-from-a-brand-domain check. Both are zero-network, zero-new-permission, computed purely from already-loaded DOM state. Deliberately does not do favicon byte-hash matching (would need cross-origin image fetches and a maintained hash database) or logo/image recognition.

In progress (experimental): Firefox groundwork. All source (`background/service-worker.ts`, `content/dom-analyzer.ts`, `warning/overlay.ts`, `popup/Popup.tsx`, `services/settings.ts`) now calls `browser.*` (via `webextension-polyfill`) instead of `chrome.*`, with Promise-based message listeners (`return Promise<unknown> | undefined` instead of `sendResponse` + `return true/false`). `manifest.json` adds `browser_specific_settings.gecko` (ignored by Chrome) and declares `background.scripts` next to `background.service_worker` — the standard cross-browser shape, since Firefox's MV3 background is an event-page `scripts` entry while Chrome uses the service worker and ignores `scripts`. **Caveat, stated plainly:** this is verified only against the Chrome-targeted unit suite, the real-Chromium E2E smoke test, and the build — it has **not** been loaded or click-tested in a real Firefox profile, and Firefox does not support module background scripts on every 115+ build, so the event-page path may not run there yet. Treat Firefox as **experimental and unverified**, not a parity guarantee. Remaining work to call it done: load and click-test in a real Firefox profile and reconcile any background/module differences.

## 5. PhishTank

Add production-grade rate-limit handling, caching, and observability around lookups.

## 6. TLS Analyzer

Improve certificate chain metadata, issuer normalization, and timeout reporting.

Done: added a Certificate Transparency freshness signal through `crt.sh`, guarded by `PHISHLENS_ENABLE_CT_LOG_LOOKUP`, as a best-effort TLS-category signal.

Done: added a sibling `domain_age` signal via RDAP (registration age), following the same cache/diagnostics pattern as TLS and PhishTank.

## 7. ML Baseline

Done: trained on a real PhishTank + Tranco dataset (1200 rows) after fixing two dataset-construction biases, URL length and subdomains (see [docs/ml-methodology.md](ml-methodology.md)). With both fixed, 5-fold CV gives 0.785 precision / 0.817 recall. Artifacts are versioned (`git_hash`, `trained_at`) in `ml/train_model.py`. A backtest of the rule-based URL heuristics (`ml/evaluate_heuristics.py`) confirmed typosquat/homograph detection carries most of the URL category's weight. Temporal validation (`ml/evaluate_temporal_drift.py`: train on phishing more than 2 years old, test on phishing less than 14 days old) gives 0.67 accuracy with 0.42 phishing recall: the URL-only model does not hold up against new campaigns. Per-prediction explainability via `shap.TreeExplainer` surfaces the top contributing features for each analysis, not just global feature importances. Remaining: better features than URL shape (domain age from RDAP as a training feature, DOM features in the dataset, which is URL-only today), periodic retraining as phishing patterns drift, and revisiting the ML adjustment's weight (up to +20) given the model's measured precision.

## 8. Advanced UI

Add richer explanations, user feedback controls, and optional high-risk warning overlays.

## 9. Publication

Prepare Chrome Web Store assets, privacy policy, screenshots, and release packaging.

## 10. Continuous Improvement

Monitor false positives, review threat intelligence sources, and maintain security dependencies.

## 11. Demo And Observability

Maintain a reproducible local demo, development diagnostics, request IDs, and rate-limit protections without expanding sensitive data collection.

## 12. Publication Readiness

Prepare Chrome Web Store checklist, permission documentation, demo readiness checks, and release artifacts without changing the privacy boundary.

## Known Remaining Work

Smaller, scoped items identified but not yet implemented:

- **TLS scoring**: add a signal for self-signed or free-CA certificates combined with a recently registered domain (`scoring_service._score_tls`), complementary to the existing expired/expiring/invalid checks.
- **Feedback retention**: `feedback_store.py` only purges entries older than 30 days at process startup (schema init), not periodically while the process stays up. A long-running deployment without restarts will accumulate rows past the documented retention window.
