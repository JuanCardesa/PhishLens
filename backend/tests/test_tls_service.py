import ssl
import unittest.mock as mock

import pytest

from app.core.config import Settings
from app.services import tls_service
from app.services.tls_service import TLSResult, _inspect_tls_sync, inspect_tls


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


def test_inspect_tls_sync_detects_expired_cert_via_verify_code(monkeypatch: pytest.MonkeyPatch) -> None:
    exc = ssl.SSLCertVerificationError()
    exc.verify_code = 10  # X509_V_ERR_CERT_HAS_EXPIRED
    exc.verify_message = "certificate has expired"

    with mock.patch("socket.create_connection") as mock_conn:
        mock_sock = mock.MagicMock()
        mock_conn.return_value.__enter__ = mock.MagicMock(return_value=mock_sock)
        mock_conn.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_sock.makefile = mock.MagicMock()

        with mock.patch("ssl.create_default_context") as mock_ctx:
            mock_ctx.return_value.wrap_socket.side_effect = exc
            result = _inspect_tls_sync("expired.example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is False
    assert result.expired is True
    assert result.days_until_expiration is None


@pytest.mark.asyncio
async def test_tls_returns_controlled_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inspect(hostname: str, timeout: float) -> TLSResult:
        return TLSResult(checked=True, valid=False, error="connection failed")

    monkeypatch.setattr(tls_service, "_inspect_tls_sync", fake_inspect)

    result = await inspect_tls("https://example.test", settings=Settings())

    assert result.checked is True
    assert result.valid is False
    assert result.error == "connection failed"
