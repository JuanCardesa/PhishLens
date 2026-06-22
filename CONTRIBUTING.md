# Contributing to PhishLens

## Requirements

- Python 3.11+
- Node 20+
- Docker (optional, for container validation)

## Setup

```bash
git clone https://github.com/JuanCardesa/PhishLens.git
cd PhishLens
cp .env.example .env

# Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt

# Extension
cd extension
npm ci
```

## Running the project locally

```bash
# Backend (from repo root, venv active)
uvicorn app.main:app --app-dir backend --reload

# Extension
cd extension && npm run build
# Then load extension/dist in Chrome via chrome://extensions → Developer mode → Load unpacked
```

## Running tests

```bash
# Backend — runs in ~5 s, no model or network required
pytest backend/tests -v

# Type checking and linting
mypy --config-file backend/mypy.ini backend/app
ruff check backend/app backend/tests

# Extension
cd extension
npm run test     # Vitest unit tests
npm run lint     # TypeScript type check
npm run build    # Verify the dist compiles
```

## ML pipeline (optional)

```bash
# Download a real dataset (~1-2 min, requires internet)
python ml/datasets/build_dataset.py

# Train and evaluate the model
python ml/train_model.py
python ml/evaluate_model.py
```

## PR checklist

Before opening a pull request, verify:

- [ ] `pytest backend/tests` passes with no failures.
- [ ] `mypy backend/app` exits 0 (strict mode).
- [ ] `ruff check backend/app backend/tests` exits 0.
- [ ] `npm run test` passes in `extension/`.
- [ ] `npm run lint` exits 0.
- [ ] `npm run build` produces a clean dist.
- [ ] If `manifest.json` changed → `docs/permissions.md` is updated.
- [ ] If scoring logic changed → scoring tests are updated.
- [ ] If analysis/report/diagnostics routes changed → privacy docs are reviewed.
- [ ] No secrets committed (PR Guardian enforces this automatically).

Run `python scripts/ci/pr_guardian.py --all` locally to simulate the CI guardrails.

## Commit conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

| Type | When to use |
|------|-------------|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | New or updated tests (no production code change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore` | Maintenance (deps, CI config, build scripts) |
| `security` | Security hardening without behaviour change |

Examples:

```
feat(popup): add React ErrorBoundary with user-facing fallback UI
fix(feedback): acquire lock in count() for thread-safe health check reads
docs(readme): add CI badges and Quick Start section
test(options): add unit tests for diagnosticsLabelFor helper
```

## Branch strategy

- `main` — stable, tagged releases only.
- `develop` — integration branch; open PRs against this branch.
- Feature branches: `feat/<short-description>`.
- Fix branches: `fix/<short-description>`.

PRs to `main` require a passing release CI run (see [docs/release-process.md](docs/release-process.md)).

## Architecture overview

See [docs/architecture.md](docs/architecture.md) for a full description of the data flow between the content script, service worker, popup, and backend API.

Privacy constraints are documented in [docs/privacy.md](docs/privacy.md). The threat model is in [docs/threat-model.md](docs/threat-model.md).
