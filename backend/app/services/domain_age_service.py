from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import Settings, get_settings
from app.services.cache import TTLCache
from app.services.diagnostics import DIAGNOSTICS
from app.services.url_normalizer import URLNormalizationError, hostname_from_url, normalize_url


RDAP_BOOTSTRAP_URL = "https://rdap.org/domain/{domain}"
# Domain registration dates do not change minute to minute, unlike TLS/PhishTank
# state, so successful lookups are cached far longer (24h) to cut down on outbound
# RDAP calls.
DOMAIN_AGE_CACHE = TTLCache["DomainAgeResult"](ttl_seconds=86400)
DOMAIN_AGE_ERROR_CACHE = TTLCache["DomainAgeResult"](ttl_seconds=30)


@dataclass(frozen=True)
class DomainAgeResult:
    checked: bool
    age_days: int | None = None
    registered_at: str | None = None
    error: str | None = None


async def check_domain_age(url: str, settings: Settings | None = None) -> DomainAgeResult:
    settings = settings or get_settings()

    if not settings.enable_domain_age_lookup:
        DIAGNOSTICS.record_external_skip("domain_age")
        return DomainAgeResult(checked=False, error="domain age lookup disabled")

    try:
        normalized_url = normalize_url(url)
    except URLNormalizationError as exc:
        DIAGNOSTICS.record_external_error("domain_age")
        return DomainAgeResult(checked=False, error=str(exc))

    hostname = hostname_from_url(normalized_url)
    if not hostname:
        DIAGNOSTICS.record_external_error("domain_age")
        return DomainAgeResult(checked=False, error="URL has no hostname")

    cache_key = hostname
    cached = DOMAIN_AGE_CACHE.get(cache_key) or DOMAIN_AGE_ERROR_CACHE.get(cache_key)
    if cached is not None:
        DIAGNOSTICS.record_cache("domain_age", hit=True)
        return cached
    DIAGNOSTICS.record_cache("domain_age", hit=False)

    try:
        payload = await _fetch_rdap_payload(hostname, settings)
    except (httpx.HTTPError, ValueError) as exc:
        DIAGNOSTICS.record_external_error("domain_age")
        result = DomainAgeResult(checked=True, error=str(exc))
        DOMAIN_AGE_ERROR_CACHE.set(cache_key, result)
        return result

    result = _parse_rdap_payload(payload)
    DOMAIN_AGE_CACHE.set(cache_key, result)
    return result


async def _fetch_rdap_payload(hostname: str, settings: Settings) -> dict[str, object]:
    async with httpx.AsyncClient(timeout=settings.external_timeout_seconds, follow_redirects=True) as client:
        response = await client.get(RDAP_BOOTSTRAP_URL.format(domain=hostname))
        response.raise_for_status()
        payload: dict[str, object] = response.json()
        return payload


def _parse_rdap_payload(payload: dict[str, object]) -> DomainAgeResult:
    events = payload.get("events")
    if not isinstance(events, list):
        return DomainAgeResult(checked=True)

    for event in events:
        if not isinstance(event, dict) or event.get("eventAction") != "registration":
            continue

        event_date = event.get("eventDate")
        if not isinstance(event_date, str):
            continue

        try:
            registered_at = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
        except ValueError:
            continue

        if registered_at.tzinfo is None:
            registered_at = registered_at.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - registered_at).days
        return DomainAgeResult(checked=True, age_days=age_days, registered_at=event_date)

    # No registration event in the response — common for privacy-protected WHOIS
    # records. Not a phishing signal by itself, so this is not treated as an error.
    return DomainAgeResult(checked=True)


def clear_domain_age_cache() -> None:
    DOMAIN_AGE_CACHE.clear()
    DOMAIN_AGE_ERROR_CACHE.clear()
