from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings
from app.services.cache import TTLCache
from app.services.diagnostics import DIAGNOSTICS
from app.services.url_normalizer import normalize_url


PHISHTANK_CHECK_URL = "http://checkurl.phishtank.com/checkurl/"
PHISHTANK_CACHE = TTLCache["PhishTankResult"](ttl_seconds=300)
PHISHTANK_ERROR_CACHE = TTLCache["PhishTankResult"](ttl_seconds=30)


@dataclass(frozen=True)
class PhishTankResult:
    checked: bool
    in_database: bool = False
    verified: bool = False
    valid: bool = False
    detail_url: str | None = None
    error: str | None = None


async def check_url(url: str, settings: Settings | None = None) -> PhishTankResult:
    settings = settings or get_settings()
    normalized_url = normalize_url(url)

    if not settings.enable_threat_intel:
        DIAGNOSTICS.record_external_skip("phishtank")
        return PhishTankResult(checked=False, error="threat intelligence disabled")

    if not settings.phishtank_api_key:
        DIAGNOSTICS.record_external_skip("phishtank")
        return PhishTankResult(checked=False, error="PHISHTANK_API_KEY is not configured")

    cached = PHISHTANK_CACHE.get(normalized_url) or PHISHTANK_ERROR_CACHE.get(normalized_url)
    if cached is not None:
        DIAGNOSTICS.record_cache("phishtank", hit=True)
        return cached
    DIAGNOSTICS.record_cache("phishtank", hit=False)

    try:
        payload = await _fetch_phishtank_payload(normalized_url, settings)
    except (httpx.HTTPError, ValueError) as exc:
        DIAGNOSTICS.record_external_error("phishtank")
        result = PhishTankResult(checked=True, error=str(exc))
        # Cache transient errors briefly (30 s) to avoid hammering PhishTank
        # during a partial outage, but allow retries much sooner than a
        # successful result would (300 s).
        PHISHTANK_ERROR_CACHE.set(normalized_url, result)
        return result

    result = payload.get("results") or {}
    phishtank_result = PhishTankResult(
        checked=True,
        in_database=_as_bool(result.get("in_database")),
        verified=_as_bool(result.get("verified")),
        valid=_as_bool(result.get("valid")),
        detail_url=result.get("phish_detail_page"),
    )
    PHISHTANK_CACHE.set(normalized_url, phishtank_result)
    return phishtank_result


async def _fetch_phishtank_payload(url: str, settings: Settings) -> dict[str, object]:
    data = {
        "url": url,
        "format": "json",
        "app_key": settings.phishtank_api_key,
    }
    headers = {"User-Agent": settings.phishtank_user_agent}

    async with httpx.AsyncClient(timeout=settings.external_timeout_seconds) as client:
        response = await client.post(PHISHTANK_CHECK_URL, data=data, headers=headers)
        response.raise_for_status()
        return response.json()


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"y", "yes", "true", "1"}
    return False


def clear_phishtank_cache() -> None:
    PHISHTANK_CACHE.clear()
    PHISHTANK_ERROR_CACHE.clear()
