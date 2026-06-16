# Release Process

PhishLens uses `main` as the public stable branch and `develop` as the integration branch.

## Normal Flow

1. Create feature branches from `develop`.
2. Open PRs back to `develop`.
3. Run backend and extension checks.
4. Run PR Guardian and security checks when the PR changes sensitive surfaces.
5. Merge into `develop`.
6. Promote `develop` to `main` through a release PR.
7. Tag the release from `main`.
8. Let the `Release Extension` workflow publish the extension zip to GitHub Releases.

See [review-methodology.md](review-methodology.md) for the full review flow.

## Validation Checklist

```bash
pytest backend/tests
ruff check backend/app backend/tests ml demo
cd extension
npm run lint
npm run test
npm run build
npm audit --audit-level=high
npm run package
```

Docker validation:

```bash
docker compose build backend
docker compose up -d backend
curl http://localhost:8000/health
docker compose stop backend
```

## Extension Package

`npm run package` writes the loadable Chrome extension zip to `extension/release/`.
The zip is a generated artifact and is not committed.

## Automated Release Workflow

`Release Extension` runs on tags matching `v*`. It validates backend tests, extension checks, dependency audit, release metadata, and then attaches the generated `phishlens-extension-v*.zip` artifact to the GitHub Release.

The workflow does not publish to npm and does not require external announcement secrets.
