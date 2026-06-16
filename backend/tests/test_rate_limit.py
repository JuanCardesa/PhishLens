from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


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
