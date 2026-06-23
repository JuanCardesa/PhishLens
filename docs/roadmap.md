# Roadmap

## 1. Bootstrap

Repository structure, Git flow, docs, CI, Docker, and safe project rules.

## 2. MVP Extension

Manifest V3 extension with popup, local URL scoring, DOM feature collection, and backend fallback behavior.

## 3. Backend FastAPI

Health, analysis, and report endpoints with Pydantic schemas and tests.

## 4. DOM Analyzer

Expand non-sensitive DOM signals while preserving the no-content and no-input-values boundary.

## 5. PhishTank

Add production-grade rate-limit handling, caching, and observability around lookups.

## 6. TLS Analyzer

Improve certificate chain metadata, issuer normalization, and timeout reporting.

Done: added a sibling `domain_age` signal via RDAP (registration age), following the same cache/diagnostics pattern as TLS and PhishTank.

## 7. ML Baseline

Done: trained on a real PhishTank + Tranco dataset (1200 rows, ~0.92 hold-out accuracy after fixing a URL-length dataset bias — see [docs/ml-methodology.md](ml-methodology.md)), with versioned artifacts (`git_hash`, `trained_at`) in `ml/train_model.py`. A backtest of the rule-based URL heuristics (`ml/evaluate_heuristics.py`) confirmed typosquat/homograph detection carries most of the URL category's weight. Remaining: periodic retraining as phishing patterns drift, domain-age (RDAP) as a training feature, and DOM-feature collection for the dataset (currently URL-only).

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
