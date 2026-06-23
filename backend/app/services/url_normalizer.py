from __future__ import annotations

import ipaddress
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urlsplit, urlunsplit


class URLNormalizationError(ValueError):
    pass


def _parse_ip_literal(hostname: str) -> IPv4Address | IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _is_private_ip(hostname: str) -> bool:
    addr = _parse_ip_literal(hostname)
    return addr is not None and not addr.is_global


def _idna_encode_hostname(hostname: str) -> str:
    try:
        return hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise URLNormalizationError("url must include a valid hostname") from exc


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower().rstrip(".") if parsed.hostname else ""

    if scheme not in {"http", "https"} or not hostname:
        raise URLNormalizationError("url must be an absolute http or https URL")

    ip_literal = _parse_ip_literal(hostname)
    if ip_literal is not None and not ip_literal.is_global:
        raise URLNormalizationError("url must not target a private or loopback address")

    try:
        port = parsed.port
    except ValueError as exc:
        raise URLNormalizationError("url must include a valid port") from exc

    # IPv6 literals must keep their brackets in the netloc, or urlunsplit
    # produces a string that re-parses with the wrong hostname (the part
    # before the first colon).
    if isinstance(ip_literal, IPv6Address):
        netloc_host = f"[{hostname}]"
    elif ip_literal is not None:
        netloc_host = hostname
    else:
        netloc_host = _idna_encode_hostname(hostname)
    netloc = f"{netloc_host}:{port}" if port is not None else netloc_host

    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def hostname_from_url(value: str) -> str | None:
    parsed = urlsplit(value)
    return parsed.hostname.lower() if parsed.hostname else None
