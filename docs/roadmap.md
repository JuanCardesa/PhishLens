# Roadmap

## 1. Bootstrap

Repository structure, Git flow, docs, CI, Docker, and safe project rules.

## 2. MVP Extension

Manifest V3 extension with popup, local URL scoring, DOM feature collection, and backend fallback behavior.

## 3. Backend FastAPI

Health, analysis, and report endpoints with Pydantic schemas and tests.

## 4. DOM Analyzer

Expand non-sensitive DOM signals while preserving the no-content and no-input-values boundary.

Done: added brand-impersonation detection — a visible-text (title/`og:site_name`/`h1`) brand mismatch against a curated brand-domain list shared with typosquat detection, plus a favicon-hotlinked-from-a-brand-domain check. Both are zero-network, zero-new-permission, computed purely from already-loaded DOM state. Deliberately does not do favicon byte-hash matching (would need cross-origin image fetches and a maintained hash database) or logo/image recognition. Remaining differentials from the Fase 4 audit (Certificate Transparency log lookups, real Firefox support) are deferred to a future session.

## 5. PhishTank

Add production-grade rate-limit handling, caching, and observability around lookups.

## 6. TLS Analyzer

Improve certificate chain metadata, issuer normalization, and timeout reporting.

Done: added a sibling `domain_age` signal via RDAP (registration age), following the same cache/diagnostics pattern as TLS and PhishTank.

## 7. ML Baseline

Done: trained on a real PhishTank + Tranco dataset (1200 rows, ~0.92 hold-out accuracy after fixing a URL-length dataset bias — see [docs/ml-methodology.md](ml-methodology.md)), with versioned artifacts (`git_hash`, `trained_at`) in `ml/train_model.py`. A backtest of the rule-based URL heuristics (`ml/evaluate_heuristics.py`) confirmed typosquat/homograph detection carries most of the URL category's weight. Temporal validation (`ml/evaluate_temporal_drift.py`, train on phishing >2 years old, test on phishing <14 days old) gave 0.91 accuracy, within noise of the random-split numbers. Per-prediction explainability via `shap.TreeExplainer` surfaces the top contributing features for each analysis, not just global feature importances. Remaining: periodic retraining as phishing patterns drift, domain-age (RDAP) as a training feature, and DOM-feature collection for the dataset (currently URL-only).

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
