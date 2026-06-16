# Review Methodology

PhishLens uses automated gates and small pull requests to keep the project reviewable without depending on a single AI reviewer.

## Branch Flow

1. Create feature branches from `develop`.
2. Open pull requests back to `develop`.
3. Promote `develop` to `main` only through a release pull request.
4. Tag releases from `main`.

Direct work on `main` is not part of the normal flow.

## Required Checks

Every pull request should pass the checks that match its scope:

- Backend CI for FastAPI, scoring, services, demo helpers, and Python tests.
- Extension CI for TypeScript, Vitest, Vite build, and extension packaging.
- PR Guardian for workflow safety, extension permission boundaries, release metadata, documentation coupling, and secret patterns.
- Security CI when dependencies, workflows, environment examples, or CI scripts change.

## PR Guardian

`PR Guardian` is the deterministic reviewer that replaces ad hoc Copilot review when quota or availability is a blocker. It does not judge product quality. It blocks changes that are easy to miss in manual review:

- Unknown workflow files under `.github/workflows/`.
- Unexpected Chrome extension permissions or host permissions.
- `<all_urls>` in the extension manifest.
- Mismatched extension versions between `manifest.json` and `package.json`.
- Workflow permissions that write issues, pull requests, discussions, workflow runs, or OIDC tokens.
- NPM publishing or Discord release automation in workflows.
- Common committed secret patterns.
- Privacy-sensitive surface changes without matching documentation updates.

The rules live in `scripts/ci/pr_guardian.py` so they can be reviewed and run locally.

## Manual Review Checklist

Before merging a pull request:

- Confirm the branch target is correct.
- Fill out the pull request template with scope, validation, and risk notes.
- Read the changed files, not only the summary.
- Check whether Chrome permissions changed.
- Check whether backend logging or diagnostics changed.
- Check whether any user data collection changed.
- Confirm tests are meaningful for the changed behavior.
- Confirm generated artifacts are not committed.

## Release Review

Release pull requests from `develop` to `main` should verify:

- Backend and extension checks are green.
- `CHANGELOG.md` reflects the release.
- Extension `manifest.json` and `package.json` versions match.
- `docs/release-process.md` still matches the release workflow.
- The GitHub release artifact is produced by `Release Extension`, not committed to the repository.
