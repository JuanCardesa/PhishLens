from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analyze_returns_explainable_score_without_external_dependencies() -> None:
    response = client.post(
        "/analyze",
        json={
            "url": "http://login-secure.example.test/account-update",
            "dom_features": {
                "has_password_field": True,
                "num_forms": 1,
                "external_form_action": True,
                "num_iframes": 0,
                "external_links_ratio": 0.25,
                "has_hidden_inputs": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_score"] >= 35
    assert payload["label"] in {"suspicious", "dangerous"}
    assert payload["sources"]["heuristics"] is True
    assert payload["sources"]["ml"] is False
    assert payload["sources"]["phishtank"] is False
    assert "Page contains a password field" in payload["reasons"]


def test_analyze_rejects_non_http_url() -> None:
    response = client.post(
        "/analyze",
        json={
            "url": "file:///etc/passwd",
            "dom_features": {},
        },
    )

    assert response.status_code == 422
