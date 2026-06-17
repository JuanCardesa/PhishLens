"""
Integration and contract tests for the full analyze/report pipeline.

These tests use FastAPI's TestClient to exercise the full request/response
path — routing, validation, scoring, and serialisation — without mocking any
internal service. External HTTP calls (PhishTank, TLS handshake) never reach
real endpoints in CI because .test TLDs and .example domains are reserved by
RFC 2606 / RFC 6761 and have no real infrastructure.

Contract assertions verify that every field the extension's TypeScript types
expect is present with the right type and within the documented bounds. If the
backend schema changes without a matching extension update (or vice versa),
these tests will catch the drift.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

_PHISHING_URL = "http://login-secure-verify.example.test/account/update"
_BENIGN_URL = "http://www.example.test/"


# ---------------------------------------------------------------------------
# Schema / contract helpers
# ---------------------------------------------------------------------------

VALID_LABELS = {"safe", "suspicious", "dangerous"}
VALID_CATEGORIES = {"url", "dom", "threat_intel", "tls", "ml"}
EXPECTED_CATEGORY_ORDER = ["url", "dom", "threat_intel", "tls", "ml"]


def _post_analyze(url: str, dom_features: dict | None = None) -> dict:
    payload: dict = {"url": url}
    if dom_features is not None:
        payload["dom_features"] = dom_features
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _assert_analysis_contract(body: dict) -> None:
    """Verify the response matches the AnalysisResponse TypeScript contract."""
    # Top-level required fields
    assert isinstance(body["risk_score"], int), "risk_score must be int"
    assert 0 <= body["risk_score"] <= 100, "risk_score out of [0, 100]"

    assert body["label"] in VALID_LABELS, f"unknown label: {body['label']}"

    assert isinstance(body["confidence"], float), "confidence must be float"
    assert 0.0 <= body["confidence"] <= 1.0, "confidence out of [0.0, 1.0]"

    assert isinstance(body["reasons"], list), "reasons must be a list"
    assert all(isinstance(r, str) for r in body["reasons"]), "every reason must be str"

    # Sources contract: AnalysisSources
    sources = body["sources"]
    assert isinstance(sources["heuristics"], bool)
    assert isinstance(sources["ml"], bool)
    assert isinstance(sources["phishtank"], bool)
    assert isinstance(sources["tls"], bool)
    assert isinstance(sources.get("demo", False), bool)

    # risk_breakdown: exactly 5 items in the documented order
    breakdown = body["risk_breakdown"]
    assert isinstance(breakdown, list), "risk_breakdown must be a list"
    assert len(breakdown) == 5, f"expected 5 breakdown items, got {len(breakdown)}"
    assert [item["category"] for item in breakdown] == EXPECTED_CATEGORY_ORDER

    for item in breakdown:
        assert item["category"] in VALID_CATEGORIES
        assert isinstance(item["score"], int), f"score must be int in {item['category']}"
        assert isinstance(item["min_score"], int)
        assert isinstance(item["max_score"], int)
        assert item["min_score"] <= item["score"] <= item["max_score"] or item["score"] < 0, (
            f"score {item['score']} outside [{item['min_score']}, {item['max_score']}]"
        )
        assert isinstance(item["reasons"], list)
        assert isinstance(item["source"], str) and item["source"]


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


def test_analyze_response_satisfies_full_contract() -> None:
    body = _post_analyze(_PHISHING_URL, {"has_password_field": True, "num_forms": 1})
    _assert_analysis_contract(body)


def test_analyze_default_dom_features_returns_valid_response() -> None:
    body = _post_analyze(_BENIGN_URL)
    _assert_analysis_contract(body)


def test_analyze_risk_score_is_clamped() -> None:
    body = _post_analyze(
        _PHISHING_URL,
        {
            "has_password_field": True,
            "num_forms": 5,
            "external_form_action": True,
            "num_iframes": 10,
            "external_links_ratio": 1.0,
            "has_hidden_inputs": True,
        },
    )
    assert 0 <= body["risk_score"] <= 100


def test_analyze_heuristics_source_always_true() -> None:
    body = _post_analyze(_BENIGN_URL)
    assert body["sources"]["heuristics"] is True


def test_analyze_breakdown_score_sum_matches_risk_score() -> None:
    body = _post_analyze(_PHISHING_URL, {"has_password_field": True})
    raw_sum = sum(item["score"] for item in body["risk_breakdown"])
    assert body["risk_score"] == max(0, min(100, raw_sum))


def test_analyze_url_breakdown_max_score_is_35() -> None:
    body = _post_analyze(_BENIGN_URL)
    url_item = next(item for item in body["risk_breakdown"] if item["category"] == "url")
    assert url_item["max_score"] == 35


def test_analyze_dom_breakdown_max_score_is_30() -> None:
    body = _post_analyze(_BENIGN_URL)
    dom_item = next(item for item in body["risk_breakdown"] if item["category"] == "dom")
    assert dom_item["max_score"] == 30


def test_analyze_ml_breakdown_bounds() -> None:
    body = _post_analyze(_BENIGN_URL)
    ml_item = next(item for item in body["risk_breakdown"] if item["category"] == "ml")
    assert ml_item["min_score"] == -10
    assert ml_item["max_score"] == 20


def test_analyze_tls_source_field_is_string() -> None:
    body = _post_analyze(_BENIGN_URL)
    tls_item = next(item for item in body["risk_breakdown"] if item["category"] == "tls")
    assert tls_item["source"] in {"tls", "fallback"}


# ---------------------------------------------------------------------------
# Full pipeline tests (analyze + report)
# ---------------------------------------------------------------------------


def test_full_analyze_then_report_flow() -> None:
    analyze_body = _post_analyze(_PHISHING_URL, {"has_password_field": True})
    assert analyze_body["label"] in VALID_LABELS

    report_response = client.post(
        "/report",
        json={
            "url": _PHISHING_URL,
            "observed_label": analyze_body["label"],
            "expected_label": "dangerous",
            "notes": "Looks like a credential harvesting page",
        },
    )
    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["status"] == "received"
    assert isinstance(report_body["message"], str)


def test_report_without_notes_is_accepted() -> None:
    response = client.post(
        "/report",
        json={
            "url": _BENIGN_URL,
            "observed_label": "dangerous",
            "expected_label": "safe",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"


# ---------------------------------------------------------------------------
# Input validation (contract with extension's request builder)
# ---------------------------------------------------------------------------


def test_non_http_url_is_rejected_with_422() -> None:
    response = client.post("/analyze", json={"url": "file:///etc/passwd"})
    assert response.status_code == 422


def test_javascript_url_is_rejected_with_422() -> None:
    response = client.post("/analyze", json={"url": "javascript:alert(1)"})
    assert response.status_code == 422


def test_missing_url_field_is_rejected_with_422() -> None:
    response = client.post("/analyze", json={"dom_features": {}})
    assert response.status_code == 422


def test_external_links_ratio_out_of_range_rejected() -> None:
    response = client.post(
        "/analyze",
        json={"url": _BENIGN_URL, "dom_features": {"external_links_ratio": 1.5}},
    )
    assert response.status_code == 422


def test_report_rejects_invalid_label() -> None:
    response = client.post(
        "/report",
        json={
            "url": _BENIGN_URL,
            "observed_label": "unknown",
            "expected_label": "safe",
        },
    )
    assert response.status_code == 422


def test_private_ip_url_is_rejected_with_422() -> None:
    for private_url in (
        "http://0.0.0.0/secret",
        "http://127.0.0.1/secret",
        "http://192.168.1.1/admin",
        "http://10.0.0.1/internal",
        "http://100.64.0.1/internal",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata service
        "http://[::1]/secret",
        "http://[fe80::1]/internal",
        "http://203.0.113.10/example",
    ):
        response = client.post("/analyze", json={"url": private_url})
        assert response.status_code == 422, f"Expected 422 for {private_url}, got {response.status_code}"
