from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


class URLNormalizationError(ValueError):
    pass


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().rstrip(".")

    if scheme not in {"http", "https"} or not netloc:
        raise URLNormalizationError("url must be an absolute http or https URL")

    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def hostname_from_url(value: str) -> str | None:
    parsed = urlsplit(value)
    return parsed.hostname.lower() if parsed.hostname else None
