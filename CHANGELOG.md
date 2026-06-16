# Changelog

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
