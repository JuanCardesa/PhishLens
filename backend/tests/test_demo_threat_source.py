from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


client = TestClient(app)


def test_demo_threat_source_is_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setenv("PHISHLENS_ENABLE_DEMO_THREAT_SOURCE", "true")
    get_settings.cache_clear()

    response = client.post(
        "/analyze",
        json={
            "url": "http://localhost:8080/phishlens-demo-dangerous-login-secure-update.html",
            "dom_features": {
                "has_password_field": True,
                "num_forms": 1,
                "external_form_action": True,
                "num_iframes": 3,
                "external_links_ratio": 0.8,
                "has_hidden_inputs": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "dangerous"
    assert payload["risk_score"] >= 70
    assert payload["sources"]["demo"] is True
    assert "Local demo threat source is enabled for this walkthrough" in payload["reasons"]


def test_demo_threat_source_is_disabled_by_default() -> None:
    response = client.post(
        "/analyze",
        json={
            "url": "http://localhost:8080/phishlens-demo-dangerous-login-secure-update.html",
            "dom_features": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["sources"]["demo"] is False
