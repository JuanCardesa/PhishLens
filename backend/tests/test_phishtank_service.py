import pytest

from app.core.config import Settings
from app.services import phishtank_service
from app.services.phishtank_service import check_url


@pytest.mark.asyncio
async def test_phishtank_returns_verified_hit_and_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def fake_fetch(url: str, settings: Settings) -> dict[str, object]:
        nonlocal calls
        calls += 1
        assert url == "https://example.test/login"
        return {
            "results": {
                "in_database": True,
                "verified": "y",
                "valid": "y",
                "phish_detail_page": "http://phishtank.test/phish_detail.php?phish_id=1",
            }
        }

    monkeypatch.setattr(phishtank_service, "_fetch_phishtank_payload", fake_fetch)
    settings = Settings(phishtank_api_key="test-key")

    first = await check_url("HTTPS://Example.Test/login#fragment", settings=settings)
    second = await check_url("https://example.test/login", settings=settings)

    assert first.checked is True
    assert first.in_database is True
    assert first.verified is True
    assert first.valid is True
    assert second == first
    assert calls == 1


@pytest.mark.asyncio
async def test_phishtank_falls_back_without_api_key() -> None:
    result = await check_url("https://example.test/login", settings=Settings(phishtank_api_key=None))

    assert result.checked is False
    assert result.error == "PHISHTANK_API_KEY is not configured"
