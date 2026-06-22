import ssl
import unittest.mock as mock

import pytest

from app.core.config import Settings
from app.services import tls_service
from app.services.tls_service import TLSResult, _format_issuer, _inspect_tls_sync, inspect_tls


def _mock_socket_returning_cert(cert: dict | None):
    mock_conn = mock.MagicMock()
    mock_sock = mock.MagicMock()
    mock_conn.return_value.__enter__ = mock.MagicMock(return_value=mock_sock)
    mock_conn.return_value.__exit__ = mock.MagicMock(return_value=False)

    mock_tls_sock = mock.MagicMock()
    mock_tls_sock.__enter__ = mock.MagicMock(return_value=mock_tls_sock)
    mock_tls_sock.__exit__ = mock.MagicMock(return_value=False)
    mock_tls_sock.getpeercert.return_value = cert

    mock_ctx = mock.MagicMock()
    mock_ctx.wrap_socket.return_value = mock_tls_sock
    return mock_conn, mock_ctx


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


@pytest.mark.asyncio
async def test_inspect_tls_skips_when_disabled() -> None:
    result = await inspect_tls("https://example.test", settings=Settings(enable_tls_analysis=False))

    assert result.checked is False
    assert result.error == "TLS analysis disabled"


@pytest.mark.asyncio
async def test_inspect_tls_skips_non_https_urls() -> None:
    result = await inspect_tls("http://example.test", settings=Settings())

    assert result.checked is False
    assert result.error == "URL does not use HTTPS"


@pytest.mark.asyncio
async def test_inspect_tls_handles_missing_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tls_service, "normalize_url", lambda value: "https:///path")

    result = await inspect_tls("https://example.test", settings=Settings())

    assert result.checked is False
    assert result.error == "URL has no hostname"


def test_inspect_tls_sync_parses_valid_certificate() -> None:
    future_expiry = "Jan  1 00:00:00 2099 GMT"
    cert = {
        "notAfter": future_expiry,
        "issuer": ((("organizationName", "Example CA"),), (("commonName", "Example CA Root"),)),
    }
    mock_conn, mock_ctx = _mock_socket_returning_cert(cert)

    with mock.patch("socket.create_connection", mock_conn):
        with mock.patch("ssl.create_default_context", return_value=mock_ctx):
            result = _inspect_tls_sync("example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is True
    assert result.expired is False
    assert result.days_until_expiration is not None and result.days_until_expiration > 0
    assert result.issuer == "organizationName=Example CA, commonName=Example CA Root"


def test_inspect_tls_sync_detects_expiry_from_certificate_date() -> None:
    past_expiry = "Jan  1 00:00:00 2000 GMT"
    cert = {"notAfter": past_expiry, "issuer": ()}
    mock_conn, mock_ctx = _mock_socket_returning_cert(cert)

    with mock.patch("socket.create_connection", mock_conn):
        with mock.patch("ssl.create_default_context", return_value=mock_ctx):
            result = _inspect_tls_sync("example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is False
    assert result.expired is True


def test_inspect_tls_sync_handles_missing_certificate() -> None:
    mock_conn, mock_ctx = _mock_socket_returning_cert(None)

    with mock.patch("socket.create_connection", mock_conn):
        with mock.patch("ssl.create_default_context", return_value=mock_ctx):
            result = _inspect_tls_sync("example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is False
    assert result.error == "could not retrieve certificate"


def test_inspect_tls_sync_handles_unparseable_expiry_date() -> None:
    cert = {"notAfter": "not-a-date", "issuer": ()}
    mock_conn, mock_ctx = _mock_socket_returning_cert(cert)

    with mock.patch("socket.create_connection", mock_conn):
        with mock.patch("ssl.create_default_context", return_value=mock_ctx):
            result = _inspect_tls_sync("example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is False
    assert result.error is not None and "could not parse certificate expiry" in result.error


def test_inspect_tls_sync_reports_non_expiry_verification_errors() -> None:
    exc = ssl.SSLCertVerificationError()
    exc.verify_code = 18  # X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN
    exc.verify_message = "self-signed certificate"

    with mock.patch("socket.create_connection") as mock_conn:
        mock_sock = mock.MagicMock()
        mock_conn.return_value.__enter__ = mock.MagicMock(return_value=mock_sock)
        mock_conn.return_value.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("ssl.create_default_context") as mock_ctx:
            mock_ctx.return_value.wrap_socket.side_effect = exc
            result = _inspect_tls_sync("self-signed.example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is False
    assert result.expired is False
    assert result.error is not None


def test_inspect_tls_sync_handles_connection_errors() -> None:
    with mock.patch("socket.create_connection", side_effect=OSError("connection refused")):
        result = _inspect_tls_sync("unreachable.example.test", timeout=4.0)

    assert result.checked is True
    assert result.valid is False
    assert result.error == "connection refused"


def test_format_issuer_flattens_relative_distinguished_names() -> None:
    issuer = ((("organizationName", "Example CA"),), (("commonName", "Example CA Root"),))
    assert _format_issuer(issuer) == "organizationName=Example CA, commonName=Example CA Root"


def test_format_issuer_returns_none_for_non_tuple_input() -> None:
    assert _format_issuer(None) is None


def test_format_issuer_returns_none_for_empty_issuer() -> None:
    assert _format_issuer(()) is None


def test_format_issuer_skips_non_tuple_relative_names() -> None:
    issuer = ("not-a-relative-name", (("commonName", "Example CA"),))
    assert _format_issuer(issuer) == "commonName=Example CA"
