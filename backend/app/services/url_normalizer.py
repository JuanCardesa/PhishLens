from __future__ import annotations

import ipaddress
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urlsplit, urlunsplit


class URLNormalizationError(ValueError):
    pass


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower().rstrip(".") if parsed.hostname else ""

    if scheme not in {"http", "https"} or not hostname:
        raise URLNormalizationError("url must be an absolute http or https URL")

    _assert_public_host(hostname)

    try:
        port = parsed.port
    except ValueError as exc:
        raise URLNormalizationError("url must include a valid port") from exc

    netloc_host = _format_netloc_host(hostname)
    if port is not None:
        netloc = f"{netloc_host}:{port}"
    else:
        netloc = netloc_host

    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def hostname_from_url(value: str) -> str | None:
    parsed = urlsplit(value)
    return parsed.hostname.lower() if parsed.hostname else None


def _assert_public_host(hostname: str) -> None:
    """Reject non-global IP literals while allowing ordinary DNS names.

    Resolving DNS names would require a network call and is outside request
    validation, so SSRF protection here focuses on literal IP addresses.
    """
    addr = _parse_ip_literal(hostname)
    if addr is not None and not addr.is_global:
        raise URLNormalizationError(f"URL targets a non-public address: {hostname}")


def _format_netloc_host(hostname: str) -> str:
    addr = _parse_ip_literal(hostname)
    if isinstance(addr, IPv6Address):
        return f"[{hostname}]"
    return hostname


def _parse_ip_literal(hostname: str) -> IPv4Address | IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None
