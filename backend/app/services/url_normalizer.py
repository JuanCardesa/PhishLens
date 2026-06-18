from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit


class URLNormalizationError(ValueError):
    pass


def _is_private_ip(hostname: str) -> bool:
    try:
        return not ipaddress.ip_address(hostname).is_global
    except ValueError:
        return False


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower().rstrip(".") if parsed.hostname else ""

    if scheme not in {"http", "https"} or not hostname:
        raise URLNormalizationError("url must be an absolute http or https URL")

    if _is_private_ip(hostname):
        raise URLNormalizationError("url must not target a private or loopback address")

    if parsed.port is not None:
        netloc = f"{hostname}:{parsed.port}"
    else:
        netloc = hostname

    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def hostname_from_url(value: str) -> str | None:
    parsed = urlsplit(value)
    return parsed.hostname.lower() if parsed.hostname else None
