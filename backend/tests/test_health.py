import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok_with_dependency_checks() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "phishlens-api"
    assert isinstance(body["checks"]["feedback_store"], bool)
    assert isinstance(body["checks"]["ml_model"], bool)


def test_health_returns_503_when_feedback_store_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenStore:
        def count(self) -> int:
            raise OSError("DB unavailable")

    monkeypatch.setattr("app.routers.health.FEEDBACK_STORE", _BrokenStore())
    response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["feedback_store"] is False
