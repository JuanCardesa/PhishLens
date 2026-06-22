# Security Policy

PhishLens is a portfolio project, not a production service handling third-party
secrets. That said, reports are taken seriously and will be triaged promptly.

## Supported Versions

Only the latest commit on `main` receives security fixes. There is no
long-term support branch.

## Reporting a Vulnerability

Do not open a public GitHub issue for security reports.

Instead, email **juancardesasosa@gmail.com** with:

- A description of the vulnerability and its impact.
- Steps to reproduce (a minimal request/payload is enough).
- The affected component (extension, backend, or ML pipeline).

You should receive an acknowledgement within 5 business days. If the report
is confirmed, a fix will be tracked in [CHANGELOG.md](CHANGELOG.md) and
credited unless you ask to stay anonymous.

## Scope

In scope:

- The FastAPI backend (`backend/`), including the analysis, diagnostics, and
  feedback endpoints.
- The Chrome extension (`extension/`), including the content script, popup,
  and background service worker.
- The ML training/inference pipeline (`ml/`).

Out of scope:

- Third-party services PhishLens calls (PhishTank, Tranco) — report those
  upstream.
- Denial-of-service reports that require unrealistic request volumes against
  a self-hosted demo instance.

## Known, Accepted Risks

These are documented design trade-offs, not bugs — see
[docs/threat-model.md](docs/threat-model.md) for the reasoning:

- The URL normalizer blocks private-IP literals but does not resolve DNS
  names before the backend's TLS handshake (SSRF via DNS rebinding).
- The in-memory rate limiter and diagnostics counters reset on backend
  restart.

If you find a way to escalate either of these beyond what the threat model
describes, that is still worth reporting.
