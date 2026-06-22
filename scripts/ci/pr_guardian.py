from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_WORKFLOWS = {
    "backend-ci.yml",
    "extension-ci.yml",
    "pr-guardian.yml",
    "release-extension.yml",
    "security-ci.yml",
}

ALLOWED_EXTENSION_PERMISSIONS = {"activeTab", "scripting", "storage"}
ALLOWED_HOST_PERMISSIONS = {"http://localhost:8000/*", "http://127.0.0.1:8000/*"}
ALLOWED_OPTIONAL_HOST_PERMISSIONS = {"http://*/*", "https://*/*"}

WORKFLOW_BANNED_PATTERNS = {
    "actions: write": "Workflow should not mutate workflow runs from PR automation.",
    "id-token: write": "OIDC publishing must be introduced through a dedicated security review.",
    "issues: write": "Issue-writing automation is not part of the current review process.",
    "pull-requests: write": "PR-writing automation is intentionally disabled for now.",
    "discussions: write": "Discussion-writing automation is not required for PhishLens releases.",
    "NPM_TOKEN": "PhishLens does not publish npm packages.",
    "npm publish": "PhishLens release artifacts are Chrome extension zip files, not npm packages.",
    "DISCORD_BOT_TOKEN": "Discord release announcements are not configured for this project.",
    "DISCORD_ANNOUNCE_CHANNEL_ID": "Discord release announcements are not configured for this project.",
}

SECRET_PATTERNS = {
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"): "Private key material must not be committed.",
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"): "Potential AWS access key detected.",
    re.compile(r"\bghp_[A-Za-z0-9_]{30,}\b"): "Potential GitHub personal access token detected.",
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"): "Potential API token detected.",
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"): "Potential Slack token detected.",
    re.compile(r"(?im)^[ \t]*(?:[A-Z0-9_]*TOKEN|[A-Z0-9_]*SECRET|[A-Z0-9_]*PASSWORD|[A-Z0-9_]*API_KEY)[ \t]*=[ \t]*[A-Za-z0-9_./+=-]{12,}[ \t]*$"): "Potential populated secret assignment detected.",
}

SENSITIVE_SURFACE_PREFIXES = (
    "backend/app/routers/analyze.py",
    "backend/app/routers/diagnostics.py",
    "backend/app/routers/report.py",
    "backend/app/schemas/",
    "backend/app/services/diagnostics.py",
    "backend/app/services/phishtank_service.py",
    "backend/app/services/tls_service.py",
    "extension/src/content/",
    "extension/src/popup/",
    "extension/src/services/analysis-api.ts",
    "extension/src/services/settings.ts",
    "extension/src/warning/",
)

SCORING_SURFACE_FILES = {
    "backend/app/services/scoring_service.py",
    "backend/app/schemas/analysis.py",
    "extension/src/utils/risk-score.ts",
    "extension/src/utils/signal-categories.ts",
    "extension/src/types/analysis.ts",
}

SCORING_TEST_FILES = {
    "backend/tests/test_analyze_endpoint.py",
    "backend/tests/test_scoring_service.py",
    "extension/src/utils/risk-score.test.ts",
    "extension/src/utils/signal-categories.test.ts",
}

PRIVACY_DOC_FILES = {
    "README.md",
    "docs/architecture.md",
    "docs/privacy.md",
    "docs/threat-model.md",
}

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}


@dataclass
class Finding:
    path: str
    message: str


def main() -> int:
    args = parse_args()
    changed_files = collect_files(args)
    failures: list[Finding] = []
    notes: list[str] = []

    failures.extend(check_workflow_allowlist(changed_files))
    failures.extend(check_workflow_permissions(changed_files))
    failures.extend(check_manifest_contract(changed_files, args.all))
    failures.extend(check_manifest_permission_docs(changed_files, args.all))
    failures.extend(check_scoring_tests(changed_files, args.all))
    failures.extend(check_sensitive_surface_docs(changed_files, args.all))
    failures.extend(check_secret_patterns(changed_files))
    failures.extend(check_release_tag(args.release_tag))

    if not changed_files:
        notes.append("No changed files were detected for this run.")

    write_summary(args.github_summary, changed_files, failures, notes)

    if failures:
        for finding in failures:
            print(f"{finding.path}: {finding.message}", file=sys.stderr)
        return 1

    print("PR Guardian passed.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PhishLens repository guardrails")
    parser.add_argument("--base-ref", help="Git base ref used to compute changed files")
    parser.add_argument("--head-ref", default="HEAD", help="Git head ref used to compute changed files")
    parser.add_argument("--all", action="store_true", help="Scan all tracked repository files")
    parser.add_argument("--release-tag", help="Release tag to compare with extension metadata")
    parser.add_argument("--github-summary", help="Optional GitHub step summary path")
    return parser.parse_args()


def collect_files(args: argparse.Namespace) -> list[str]:
    if args.all or not args.base_ref:
        tracked = git_lines(["ls-files"])
        untracked = git_lines(["ls-files", "--others", "--exclude-standard"])
        return sorted(set(tracked + untracked))

    changed = git_lines(["diff", "--name-only", f"{args.base_ref}...{args.head_ref}"])
    return sorted(file_path for file_path in changed if file_path)


def git_lines(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def check_workflow_allowlist(files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for file_path in files:
        path = Path(file_path)
        if path.parts[:2] == (".github", "workflows") and path.name not in ALLOWED_WORKFLOWS:
            findings.append(
                Finding(
                    file_path,
                    f"Workflow is not in the PhishLens allowlist: {', '.join(sorted(ALLOWED_WORKFLOWS))}.",
                )
            )
    return findings


def check_workflow_permissions(files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for file_path in files:
        path = Path(file_path)
        if path.parts[:2] != (".github", "workflows") or not (REPO_ROOT / path).exists():
            continue

        content = read_text(path)
        for pattern, message in WORKFLOW_BANNED_PATTERNS.items():
            if pattern in content:
                findings.append(Finding(file_path, message))

        if "contents: write" in content and path.name != "release-extension.yml":
            findings.append(Finding(file_path, "Only release-extension.yml may request contents: write."))

    return findings


def check_manifest_contract(files: list[str], scan_all: bool) -> list[Finding]:
    if not scan_all and "extension/manifest.json" not in files and "extension/package.json" not in files:
        return []

    manifest_path = REPO_ROOT / "extension/manifest.json"
    package_path = REPO_ROOT / "extension/package.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_json = json.loads(package_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []

    if manifest.get("manifest_version") != 3:
        findings.append(Finding("extension/manifest.json", "Chrome extension must remain Manifest V3."))

    permissions = set(manifest.get("permissions", []))
    unexpected_permissions = permissions - ALLOWED_EXTENSION_PERMISSIONS
    if unexpected_permissions:
        findings.append(
            Finding(
                "extension/manifest.json",
                f"Unexpected extension permissions: {', '.join(sorted(unexpected_permissions))}.",
            )
        )

    host_permissions = set(manifest.get("host_permissions", []))
    unexpected_hosts = host_permissions - ALLOWED_HOST_PERMISSIONS
    if unexpected_hosts:
        findings.append(
            Finding(
                "extension/manifest.json",
                f"Unexpected required host permissions: {', '.join(sorted(unexpected_hosts))}.",
            )
        )

    optional_host_permissions = set(manifest.get("optional_host_permissions", []))
    unexpected_optional = optional_host_permissions - ALLOWED_OPTIONAL_HOST_PERMISSIONS
    if unexpected_optional:
        findings.append(
            Finding(
                "extension/manifest.json",
                f"Unexpected optional host permissions: {', '.join(sorted(unexpected_optional))}.",
            )
        )

    if "<all_urls>" in host_permissions or "<all_urls>" in optional_host_permissions:
        findings.append(Finding("extension/manifest.json", "<all_urls> is not allowed."))

    if manifest.get("version") != package_json.get("version"):
        findings.append(Finding("extension/manifest.json", "Manifest version must match extension/package.json."))

    return findings


def check_manifest_permission_docs(files: list[str], scan_all: bool) -> list[Finding]:
    if scan_all:
        return []

    changed = set(files)
    if "extension/manifest.json" in changed and "docs/permissions.md" not in changed:
        return [
            Finding(
                "extension/manifest.json",
                "Manifest permission changes must review and update docs/permissions.md.",
            )
        ]

    return []


def check_scoring_tests(files: list[str], scan_all: bool) -> list[Finding]:
    if scan_all:
        return []

    changed = set(files)
    scoring_changes = changed & SCORING_SURFACE_FILES
    if scoring_changes and not (changed & SCORING_TEST_FILES):
        return [
            Finding(
                sorted(scoring_changes)[0],
                "Scoring contract changes must include backend or extension scoring tests.",
            )
        ]

    return []


def check_sensitive_surface_docs(files: list[str], scan_all: bool) -> list[Finding]:
    if scan_all:
        return []

    changed = set(files)
    sensitive_changes = [
        file_path
        for file_path in changed
        if any(file_path == prefix or file_path.startswith(prefix) for prefix in SENSITIVE_SURFACE_PREFIXES)
        and not file_path.endswith((".test.ts", ".test.tsx"))
        and not file_path.startswith("backend/tests/")
    ]

    if sensitive_changes and not (changed & PRIVACY_DOC_FILES):
        return [
            Finding(
                sensitive_changes[0],
                "Changes to analysis, reporting, diagnostics, DOM, or overlay surfaces must update README or docs/privacy.md, docs/architecture.md, or docs/threat-model.md.",
            )
        ]

    return []


def check_secret_patterns(files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for file_path in files:
        path = Path(file_path)
        absolute_path = REPO_ROOT / path
        if not absolute_path.exists() or not should_scan_text(path):
            continue

        content = read_text(path)
        for pattern, message in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(Finding(file_path, message))
    return findings


def should_scan_text(path: Path) -> bool:
    if any(part in {"node_modules", "dist", "release", ".venv", ".git"} for part in path.parts):
        return False
    return path.suffix in TEXT_EXTENSIONS or path.name in {".env.example", ".gitignore"}


def check_release_tag(release_tag: str | None) -> list[Finding]:
    if not release_tag:
        return []

    normalized_tag = release_tag[1:] if release_tag.startswith("v") else release_tag
    manifest = json.loads((REPO_ROOT / "extension/manifest.json").read_text(encoding="utf-8"))
    package_json = json.loads((REPO_ROOT / "extension/package.json").read_text(encoding="utf-8"))

    expected_versions = {manifest.get("version"), package_json.get("version")}
    if expected_versions != {normalized_tag}:
        return [
            Finding(
                "extension/package.json",
                f"Release tag {release_tag} must match extension/package.json and extension/manifest.json versions.",
            )
        ]
    return []


def read_text(path: Path) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")


def write_summary(summary_path: str | None, files: list[str], failures: list[Finding], notes: list[str]) -> None:
    if not summary_path:
        return

    lines = [
        "# PR Guardian",
        "",
        f"Scanned files: {len(files)}",
        "",
    ]

    if failures:
        lines.append("## Failures")
        lines.append("")
        for finding in failures:
            lines.append(f"- `{finding.path}`: {finding.message}")
    else:
        lines.append("No guardrail failures detected.")

    if notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")

    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
