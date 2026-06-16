# Release Process

PhishLens uses `main` as the public stable branch and `develop` as the integration branch.

## Normal Flow

1. Create feature branches from `develop`.
2. Open PRs back to `develop`.
3. Run backend and extension checks.
4. Request Copilot review when the PR is ready.
5. Merge into `develop`.
6. Promote `develop` to `main` through a release PR.
7. Tag the release from `main`.
8. Publish a GitHub Release with the extension zip when appropriate.

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
