from __future__ import annotations

import asyncio
import socket
import ssl
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.core.config import Settings, get_settings
from app.services.cache import TTLCache
from app.services.diagnostics import DIAGNOSTICS
from app.services.url_normalizer import normalize_url


TLS_CACHE = TTLCache["TLSResult"](ttl_seconds=300)

# OpenSSL verify error code for an expired certificate.
_OPENSSL_ERR_CERT_HAS_EXPIRED = 10

# crt.sh queries a fixed third-party host with the hostname as a query
# parameter — like the RDAP domain-age lookup, it never connects to the
# analyzed host directly, so it does not share the raw socket TLS check's
# DNS-rebinding SSRF exposure (see docs/threat-model.md).
CT_LOG_QUERY_URL = "https://crt.sh/?q={domain}&output=json"


@dataclass(frozen=True)
class TLSResult:
    checked: bool
    valid: bool = False
    days_until_expiration: int | None = None
    issuer: str | None = None
    expired: bool = False
    error: str | None = None
    ct_logs_checked: bool = False
    ct_first_seen_days_ago: int | None = None
    ct_error: str | None = None


async def inspect_tls(url: str, settings: Settings | None = None) -> TLSResult:
    settings = settings or get_settings()
    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)

    if not settings.enable_tls_analysis:
        DIAGNOSTICS.record_external_skip("tls")
        return TLSResult(checked=False, error="TLS analysis disabled")

    if parsed.scheme != "https":
        DIAGNOSTICS.record_external_skip("tls")
        return TLSResult(checked=False, error="URL does not use HTTPS")

    hostname = parsed.hostname
    if not hostname:
        DIAGNOSTICS.record_external_error("tls")
        return TLSResult(checked=False, error="URL has no hostname")

    cache_key = hostname.lower()
    cached = TLS_CACHE.get(cache_key)
    if cached is not None:
        DIAGNOSTICS.record_cache("tls", hit=True)
        return cached
    DIAGNOSTICS.record_cache("tls", hit=False)

    cert_result, ct_result = await asyncio.gather(
        asyncio.to_thread(_inspect_tls_sync, hostname, settings.external_timeout_seconds),
        _check_ct_logs(hostname, settings),
    )
    ct_logs_checked, ct_first_seen_days_ago, ct_error = ct_result
    result = replace(
        cert_result,
        ct_logs_checked=ct_logs_checked,
        ct_first_seen_days_ago=ct_first_seen_days_ago,
        ct_error=ct_error,
    )
    if result.error:
        DIAGNOSTICS.record_external_error("tls")
    TLS_CACHE.set(cache_key, result)
    return result


def _inspect_tls_sync(hostname: str, timeout: float) -> TLSResult:
    server_name = hostname.encode("idna").decode("ascii")
    context = ssl.create_default_context()

    try:
        with socket.create_connection((server_name, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=server_name) as tls_sock:
                cert = tls_sock.getpeercert()
    except ssl.SSLCertVerificationError as exc:
        # Python's ssl raises before the handshake completes for expired certs,
        # so we never reach the post-handshake parsing. Inspect the OpenSSL
        # verify code directly to distinguish expiry from other failures.
        if exc.verify_code == _OPENSSL_ERR_CERT_HAS_EXPIRED:
            return TLSResult(checked=True, valid=False, expired=True)
        return TLSResult(checked=True, valid=False, error=str(exc))
    except Exception as exc:
        return TLSResult(checked=True, valid=False, error=str(exc))

    if cert is None:
        return TLSResult(checked=True, valid=False, error="could not retrieve certificate")

    try:
        not_after = str(cert["notAfter"])
        expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_until_expiration = (expires_at - datetime.now(timezone.utc)).days
        expired = days_until_expiration < 0
    except (KeyError, ValueError) as exc:
        return TLSResult(checked=True, valid=False, error=f"could not parse certificate expiry: {exc}")

    issuer = _format_issuer(cert.get("issuer", ()))
    return TLSResult(
        checked=True,
        valid=not expired,
        days_until_expiration=days_until_expiration,
        issuer=issuer,
        expired=expired,
    )


def _format_issuer(issuer_parts: object) -> str | None:
    flattened: list[str] = []
    if not isinstance(issuer_parts, tuple):
        return None

    for relative_name in issuer_parts:
        if not isinstance(relative_name, tuple):
            continue
        for key_value in relative_name:
            if isinstance(key_value, tuple) and len(key_value) == 2:
                flattened.append(f"{key_value[0]}={key_value[1]}")

    return ", ".join(flattened) if flattened else None


async def _check_ct_logs(hostname: str, settings: Settings) -> tuple[bool, int | None, str | None]:
    """Returns (checked, first_seen_days_ago, error). Best-effort: any failure
    here must never block the rest of the TLS result, since CT log coverage
    and crt.sh availability are not guaranteed (see docs/threat-model.md)."""
    if not settings.enable_ct_log_lookup:
        return False, None, "CT log lookup disabled"

    try:
        payload = await _fetch_ct_log_payload(hostname, settings)
    except (httpx.HTTPError, ValueError) as exc:
        return False, None, str(exc)

    return True, _earliest_ct_entry_days_ago(payload), None


async def _fetch_ct_log_payload(hostname: str, settings: Settings) -> list[dict[str, object]]:
    async with httpx.AsyncClient(timeout=settings.external_timeout_seconds, follow_redirects=True) as client:
        response = await client.get(CT_LOG_QUERY_URL.format(domain=hostname))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("unexpected crt.sh response shape")
        return payload


def _earliest_ct_entry_days_ago(entries: list[dict[str, object]]) -> int | None:
    earliest: datetime | None = None

    for entry in entries:
        not_before = entry.get("not_before") if isinstance(entry, dict) else None
        if not isinstance(not_before, str):
            continue

        try:
            issued_at = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
        except ValueError:
            continue

        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)

        if earliest is None or issued_at < earliest:
            earliest = issued_at

    if earliest is None:
        return None

    return (datetime.now(timezone.utc) - earliest).days


def clear_tls_cache() -> None:
    TLS_CACHE.clear()
