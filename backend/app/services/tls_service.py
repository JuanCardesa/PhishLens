from __future__ import annotations

import asyncio
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.services.cache import TTLCache
from app.services.diagnostics import DIAGNOSTICS
from app.services.url_normalizer import normalize_url


TLS_CACHE = TTLCache["TLSResult"](ttl_seconds=300)


@dataclass(frozen=True)
class TLSResult:
    checked: bool
    valid: bool = False
    days_until_expiration: int | None = None
    issuer: str | None = None
    expired: bool = False
    error: str | None = None


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

    result = await asyncio.to_thread(_inspect_tls_sync, hostname, settings.external_timeout_seconds)
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
    except Exception as exc:
        return TLSResult(checked=True, valid=False, error=str(exc))

    try:
        expires_at = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
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


def clear_tls_cache() -> None:
    TLS_CACHE.clear()
