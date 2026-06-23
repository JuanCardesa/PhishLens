from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.services import domain_age_service
from app.services.domain_age_service import check_domain_age


def _registration_payload(days_ago: int) -> dict[str, object]:
    event_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")
    return {"events": [{"eventAction": "registration", "eventDate": event_date}]}


@pytest.mark.asyncio
async def test_recently_registered_domain_reports_age_and_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def fake_fetch(hostname: str, settings: Settings) -> dict[str, object]:
        nonlocal calls
        calls += 1
        assert hostname == "example.test"
        return _registration_payload(days_ago=5)

    monkeypatch.setattr(domain_age_service, "_fetch_rdap_payload", fake_fetch)
    settings = Settings(enable_domain_age_lookup=True)

    first = await check_domain_age("https://Example.Test/login#fragment", settings=settings)
    second = await check_domain_age("https://example.test/login", settings=settings)

    assert first.checked is True
    assert first.age_days == 5
    assert second == first
    assert calls == 1


@pytest.mark.asyncio
async def test_old_domain_reports_large_age(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(hostname: str, settings: Settings) -> dict[str, object]:
        return _registration_payload(days_ago=3650)

    monkeypatch.setattr(domain_age_service, "_fetch_rdap_payload", fake_fetch)

    result = await check_domain_age("https://example.test", settings=Settings(enable_domain_age_lookup=True))

    assert result.checked is True
    assert result.age_days == 3650


@pytest.mark.asyncio
async def test_missing_registration_event_returns_checked_without_age(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(hostname: str, settings: Settings) -> dict[str, object]:
        return {"events": [{"eventAction": "last changed", "eventDate": "2020-01-01T00:00:00Z"}]}

    monkeypatch.setattr(domain_age_service, "_fetch_rdap_payload", fake_fetch)

    result = await check_domain_age("https://example.test", settings=Settings(enable_domain_age_lookup=True))

    assert result.checked is True
    assert result.age_days is None
    assert result.error is None


@pytest.mark.asyncio
async def test_network_error_is_cached_briefly_and_not_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(hostname: str, settings: Settings) -> dict[str, object]:
        raise ValueError("boom")

    monkeypatch.setattr(domain_age_service, "_fetch_rdap_payload", fake_fetch)

    result = await check_domain_age("https://example.test", settings=Settings(enable_domain_age_lookup=True))

    assert result.checked is True
    assert result.age_days is None
    assert result.error == "boom"


@pytest.mark.asyncio
async def test_disabled_by_settings_skips_lookup() -> None:
    result = await check_domain_age(
        "https://example.test", settings=Settings(enable_domain_age_lookup=False)
    )

    assert result.checked is False
    assert result.error == "domain age lookup disabled"
