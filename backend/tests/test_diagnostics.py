from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_request_id_header_is_returned() -> None:
    response = client.get("/health", headers={"X-Request-ID": "demo-request-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "demo-request-1"


def test_diagnostics_tracks_counts_without_sensitive_payloads() -> None:
    analyze_response = client.post(
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
    assert analyze_response.status_code == 200

    diagnostics_response = client.get("/diagnostics")

    assert diagnostics_response.status_code == 200
    payload = diagnostics_response.json()
    assert payload["status"] == "ok"
    assert payload["counters"]["analysis_requests"] == 1
    assert payload["sources"]["heuristics"] == 1
    assert "login-secure.example.test" not in str(payload)
    assert "password" not in str(payload).lower()


def test_validation_errors_do_not_echo_submitted_input() -> None:
    response = client.post(
        "/analyze",
        json={
            "url": "file:///Users/example/private-token",
            "dom_features": {},
        },
    )

    assert response.status_code == 422
    payload_text = response.text
    assert "Request validation failed" in payload_text
    assert "private-token" not in payload_text
