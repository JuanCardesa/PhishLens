"""
Parity tests for the URL and DOM scoring functions.

Each vector here has a matching test in
extension/src/utils/risk-score.test.ts (the "scoring parity" describe block).
If values diverge between the two files the offline TypeScript fallback and
the backend are scoring differently; both files must be updated together.
"""
from __future__ import annotations

from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import extract_url_features
from app.services.scoring_service import _score_dom, _score_url, label_from_score

EMPTY_DOM = DOMFeatures()


def test_benign_https_url_scores_zero() -> None:
    features = extract_url_features("https://example.com")
    score, reasons = _score_url(features)
    assert score == 0
    assert reasons == []


def test_no_https_adds_five_points() -> None:
    features = extract_url_features("http://example.com")
    score, _ = _score_url(features)
    assert score == 5


def test_two_keywords_and_no_https_gives_thirteen() -> None:
    # http (+5) + keywords 'secure','login' -> min(8, 4*2=8)=8 -> total 13
    features = extract_url_features("http://secure-login.example.com")
    score, reasons = _score_url(features)
    assert score == 13
    assert "URL does not use HTTPS" in reasons
    assert "Domain or path contains suspicious keywords" in reasons


def test_empty_dom_scores_zero() -> None:
    score, reasons = _score_dom(EMPTY_DOM)
    assert score == 0
    assert reasons == []


def test_password_form_with_external_action_dom_score() -> None:
    # forms (+4) + password (+8) + external action (+10) = 22
    dom = DOMFeatures(has_password_field=True, num_forms=1, external_form_action=True)
    score, _ = _score_dom(dom)
    assert score == 22


def test_combined_score_and_label_suspicious() -> None:
    # url 13 + dom 22 = 35 -> suspicious
    url_features = extract_url_features("http://secure-login.example.com")
    url_score, _ = _score_url(url_features)
    dom = DOMFeatures(has_password_field=True, num_forms=1, external_form_action=True)
    dom_score, _ = _score_dom(dom)
    total = url_score + dom_score
    assert total == 35
    assert label_from_score(total) == "suspicious"


def test_num_dots_excludes_query_string() -> None:
    # Query string dots must not change the num_dots count
    with_qs = extract_url_features("https://maps.example.com?q=1.5,2.3&zoom=1.0")
    without_qs = extract_url_features("https://maps.example.com")
    assert with_qs.num_dots == without_qs.num_dots


def test_url_score_cap_is_35() -> None:
    features = extract_url_features(
        "http://secure-login-verify-account-update-password-bank.attacker.phishing.scam.evil.bad.com/wallet"
    )
    score, _ = _score_url(features)
    assert score <= 35
