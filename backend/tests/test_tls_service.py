import pytest

from app.core.config import Settings
from app.services import tls_service
from app.services.tls_service import TLSResult, inspect_tls


@pytest.mark.asyncio
async def test_tls_returns_expired_certificate_and_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_inspect(hostname: str, timeout: float) -> TLSResult:
        nonlocal calls
        calls += 1
        assert hostname == "example.test"
        return TLSResult(checked=True, valid=False, expired=True, days_until_expiration=-2, issuer="CN=test")

    monkeypatch.setattr(tls_service, "_inspect_tls_sync", fake_inspect)

    first = await inspect_tls("HTTPS://Example.Test/login#fragment", settings=Settings())
    second = await inspect_tls("https://example.test/other", settings=Settings())

    assert first.checked is True
    assert first.expired is True
    assert second == first
    assert calls == 1


@pytest.mark.asyncio
async def test_tls_returns_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inspect(hostname: str, timeout: float) -> TLSResult:
        return TLSResult(checked=True, valid=False, error="connection failed")

    monkeypatch.setattr(tls_service, "_inspect_tls_sync", fake_inspect)

    result = await inspect_tls("https://example.test", settings=Settings())

    assert result.checked is True
    assert result.valid is False
    assert result.error == "connection failed"
