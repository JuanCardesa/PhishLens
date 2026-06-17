from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.rate_limiter import _resolve_client_ip


client = TestClient(app)


def test_analyze_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setenv("PHISHLENS_ANALYZE_RATE_LIMIT", "1")
    monkeypatch.setenv("PHISHLENS_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()

    payload = {
        "url": "http://safe.example.test/",
        "dom_features": {},
    }

    first_response = client.post("/analyze", json=payload)
    second_response = client.post("/analyze", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.headers["Retry-After"].isdigit()


def test_resolve_client_ip_direct() -> None:
    request = MagicMock()
    request.client.host = "10.0.0.1"
    request.headers.get.return_value = ""
    assert _resolve_client_ip(request, behind_proxy=False) == "10.0.0.1"


def test_resolve_client_ip_behind_proxy_uses_forwarded_for() -> None:
    request = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers.get.return_value = "203.0.113.5, 10.0.0.1"
    assert _resolve_client_ip(request, behind_proxy=True) == "203.0.113.5"


def test_resolve_client_ip_behind_proxy_falls_back_when_header_missing() -> None:
    request = MagicMock()
    request.client.host = "172.16.0.2"
    request.headers.get.return_value = ""
    assert _resolve_client_ip(request, behind_proxy=True) == "172.16.0.2"


def test_rate_limit_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("PHISHLENS_ENABLE_RATE_LIMITING", "false")
    monkeypatch.setenv("PHISHLENS_ANALYZE_RATE_LIMIT", "1")
    get_settings.cache_clear()

    payload = {
        "url": "http://safe.example.test/",
        "dom_features": {},
    }

    assert client.post("/analyze", json=payload).status_code == 200
    assert client.post("/analyze", json=payload).status_code == 200
