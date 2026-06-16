## Summary

- 

## Scope

- [ ] Backend
- [ ] Extension
- [ ] ML/demo pipeline
- [ ] Documentation
- [ ] CI/release tooling
- [ ] Security/privacy surface

## Risk Review

- [ ] Chrome extension permissions are unchanged or justified below.
- [ ] No credentials, form values, cookies, tokens, full HTML, or typed emails are collected.
- [ ] Backend logs do not include sensitive payloads.
- [ ] New environment variables or secrets are documented in `.env.example`.
- [ ] Workflow permission changes are minimal and justified below.

## Validation

- [ ] `pytest backend/tests`
- [ ] `ruff check backend/app backend/tests ml demo scripts/ci`
- [ ] `cd extension && npm run lint`
- [ ] `cd extension && npm run test`
- [ ] `cd extension && npm run build`
- [ ] `cd extension && npm audit --audit-level=high`
- [ ] `python scripts/ci/pr_guardian.py --all`
- [ ] Not applicable: explain below.

## Notes For Reviewers

Call out any permissions, telemetry, diagnostics, release, dependency, or privacy-sensitive changes here.
