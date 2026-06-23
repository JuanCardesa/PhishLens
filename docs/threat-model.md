# Threat Model

## Protected Assets

- User credentials and private form input.
- User browsing privacy.
- Backend API keys.
- Extension integrity.
- Risk scoring trustworthiness.

## Risks

- Overcollection of sensitive page data.
- API key exposure in the extension bundle.
- False positives on legitimate login pages.
- False negatives on new phishing campaigns.
- Backend dependency or threat-intel outage.
- Malicious pages attempting to confuse DOM feature extraction.
- SSRF via DNS resolution: the URL normalizer blocks private IP literals but does not resolve DNS names. A hostname that resolves to a private or link-local address (e.g. an internal DNS entry or a DNS-rebinding attack) passes the literal check and reaches the TLS service's TCP connection.

## Assumptions

- The extension is installed by the user in a trusted browser profile.
- The backend is controlled by the project owner.
- PhishTank availability and rate limits are not guaranteed.
- TLS analysis from the backend may not match the user's browser path.
- RDAP domain age lookups go to a fixed third-party bootstrap host (`rdap.org`), not to
  the analyzed hostname directly, so they do not share the TLS service's DNS-rebinding
  SSRF exposure described above. Availability and per-registry rate limits are not
  guaranteed.

## Possible Abuse

- Repurposing the extension to collect credentials.
- Adding remote code loading to bypass review.
- Sending full page content to the backend.
- Treating demo ML metrics as production evidence.

## Mitigations

- Minimum Chrome permissions.
- No form values or full HTML collection.
- Backend-only API keys.
- Explicit docs for limitations and privacy boundaries.
- Tests around scoring and schemas.
- Conventional commits and reviewable changes.
- Constant-time comparison (`hmac.compare_digest`) for the `X-Diagnostics-Token` check, avoiding a timing side-channel on token validation.

## Accepted Risks And Limitations

**SSRF via DNS name resolution.** Blocking IP literals at request time without resolving DNS names is a deliberate trade-off. Resolving every submitted hostname before connecting would add latency, require a DNS dependency on the backend, and introduce a TOCTOU window between the resolution check and the actual connection. The accepted risk is that an attacker-controlled hostname resolving to a private address could reach internal services via the TLS inspection path. This is mitigated by the fact that the backend only makes a TLS handshake (no HTTP request body is sent to the target), the connection is limited to port 443, and the backend runs as a non-root user in a container. A network-level egress firewall blocking RFC 1918 ranges is the recommended control for production deployments.
