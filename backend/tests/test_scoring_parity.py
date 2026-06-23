"""
Parity tests for the URL and DOM scoring functions.

Each vector here has a matching test in
extension/src/utils/risk-score.test.ts (the "scoring parity" describe block).
If values diverge between the two files the offline TypeScript fallback and
the backend are scoring differently; both files must be updated together.
"""
from __future__ import annotations

from app.schemas.analysis import AnalysisRequest, DOMFeatures
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


def test_typosquat_domain_adds_fourteen_points() -> None:
    # https (+0) + typosquat (+14) = 14
    features = extract_url_features("https://paypa1.com")
    score, reasons = _score_url(features)
    assert score == 14
    assert "Domain closely resembles paypal.com (possible typosquatting)" in reasons


def test_full_script_homograph_adds_sixteen_points() -> None:
    # https (+0) + homograph (+16) = 16
    # xn--80ak6aa92e decodes to a Cyrillic look-alike of "apple".
    features = extract_url_features("https://xn--80ak6aa92e.com")
    score, reasons = _score_url(features)
    assert score == 16
    assert "Domain uses look-alike Unicode characters resembling apple.com (homograph attack)" in reasons


def test_mixed_script_homograph_adds_homograph_and_mixed_script_points() -> None:
    # homograph (+16) + mixed-script (+8) = 24.
    # xn--ggle-55da is the real punycode form of g + two Cyrillic o's + gle.
    features = extract_url_features("https://xn--ggle-55da.com")
    score, reasons = _score_url(features)
    assert score == 24
    assert "Domain label mixes multiple writing scripts (possible homograph attack)" in reasons
    assert "Domain uses look-alike Unicode characters resembling google.com (homograph attack)" in reasons


def test_unicode_literal_homograph_matches_punycode_score() -> None:
    unicode_url = AnalysisRequest(url="https://g\u043e\u043egle.com", dom_features=EMPTY_DOM).url
    punycode_features = extract_url_features("https://xn--ggle-55da.com")
    unicode_features = extract_url_features(unicode_url)

    punycode_score, punycode_reasons = _score_url(punycode_features)
    unicode_score, unicode_reasons = _score_url(unicode_features)

    assert unicode_url == "https://xn--ggle-55da.com"
    assert unicode_score == punycode_score == 24
    assert unicode_reasons == punycode_reasons


def test_benign_idn_scores_zero_url_points() -> None:
    features = extract_url_features("https://xn--bcher-kva.de")
    score, reasons = _score_url(features)
    assert score == 0
    assert reasons == []


def test_url_score_cap_is_35() -> None:
    features = extract_url_features(
        "http://secure-login-verify-account-update-password-bank.attacker.phishing.scam.evil.bad.com/wallet"
    )
    score, _ = _score_url(features)
    assert score <= 35
