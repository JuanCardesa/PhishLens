from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKEND_URL = "http://localhost:8000"

REQUIRED_FILES = [
    "backend/app/main.py",
    "backend/requirements.txt",
    "demo/pages/safe.html",
    "demo/pages/suspicious.html",
    "demo/pages/phishlens-demo-dangerous-login-secure-update.html",
    "docs/chrome-web-store.md",
    "docs/permissions.md",
    "docs/privacy.md",
    "extension/manifest.json",
    "extension/package.json",
    "extension/scripts/package-extension.mjs",
]

SENSITIVE_DIAGNOSTIC_TERMS = [
    "login-secure.example.test",
    "private-token",
    "form_values",
    "session_token",
]


@dataclass
class CheckResult:
    name: str
    status: str
    message: str


def main() -> int:
    args = parse_args()
    results: list[CheckResult] = []
    results.extend(check_required_files())
    results.append(check_extension_versions())
    results.extend(check_backend(args.backend_url, args.require_backend))

    for result in results:
        print(f"[{result.status}] {result.name}: {result.message}")

    return 1 if any(result.status == "FAIL" for result in results) else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check PhishLens local demo readiness")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL, help="Backend base URL to check")
    parser.add_argument("--require-backend", action="store_true", help="Fail when backend health is unavailable")
    return parser.parse_args()


def check_required_files() -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        status = "PASS" if path.exists() else "FAIL"
        message = "present" if path.exists() else "missing"
        results.append(CheckResult(relative_path, status, message))
    return results


def check_extension_versions() -> CheckResult:
    manifest = read_json(REPO_ROOT / "extension/manifest.json")
    package_json = read_json(REPO_ROOT / "extension/package.json")

    if manifest.get("version") != package_json.get("version"):
        return CheckResult("extension version", "FAIL", "manifest.json and package.json versions differ")

    return CheckResult("extension version", "PASS", f"version {manifest.get('version')}")


def check_backend(backend_url: str, require_backend: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    health = fetch_json(f"{backend_url.rstrip('/')}/health")

    if health is None:
        status = "FAIL" if require_backend else "WARN"
        return [CheckResult("backend health", status, f"{backend_url} is unavailable")]

    results.append(CheckResult("backend health", "PASS", f"{health.get('service', 'unknown')} is online"))
    diagnostics = fetch_json(f"{backend_url.rstrip('/')}/diagnostics")

    if diagnostics is None:
        results.append(CheckResult("backend diagnostics", "WARN", "diagnostics endpoint unavailable or disabled"))
        return results

    diagnostics_text = json.dumps(diagnostics, sort_keys=True).lower()
    leaked_terms = [term for term in SENSITIVE_DIAGNOSTIC_TERMS if term in diagnostics_text]
    if leaked_terms:
        results.append(CheckResult("diagnostics privacy", "FAIL", f"unexpected sensitive terms: {', '.join(leaked_terms)}"))
    else:
        results.append(CheckResult("diagnostics privacy", "PASS", "aggregate counters only"))

    return results


def fetch_json(url: str) -> dict[str, object] | None:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
