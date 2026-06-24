import pytest

from app.schemas.analysis import AnalysisRequest, DOMFeatures
from app.services.demo_threat_service import DemoThreatResult
from app.services.domain_age_service import DomainAgeResult
from app.services.feature_extractor import URLFeatures
from app.services.ml_service import MLResult
from app.services.phishtank_service import PhishTankResult
from app.services.scoring_service import (
    DOM_SCORE_CAP,
    DOMAIN_AGE_SCORE_CAP,
    ML_MAX_ADJUSTMENT,
    ML_MIN_ADJUSTMENT,
    THREAT_INTEL_SCORE_CAP,
    TLS_SCORE_CAP,
    URL_SCORE_CAP,
    _build_risk_breakdown,
    _score_dom,
    _score_domain_age,
    _score_threat_intel,
    _score_tls,
    _score_url,
    analyze_url,
    label_from_score,
)
from app.services.tls_service import TLSResult


def test_label_from_score_thresholds() -> None:
    assert label_from_score(0) == "safe"
    assert label_from_score(34) == "safe"
    assert label_from_score(35) == "suspicious"
    assert label_from_score(69) == "suspicious"
    assert label_from_score(70) == "dangerous"


def test_score_tls_expired_and_invalid_is_mutually_exclusive() -> None:
    score, reasons = _score_tls(TLSResult(checked=True, valid=False, expired=True))

    assert score == 15
    assert reasons == ["TLS certificate appears to be expired"]


def test_score_tls_invalid_without_expiry_data() -> None:
    score, reasons = _score_tls(TLSResult(checked=True, valid=False, expired=False))

    assert score == 10
    assert reasons == ["TLS certificate could not be validated"]


def test_score_tls_adds_points_for_a_brand_new_ct_log_entry() -> None:
    score, reasons = _score_tls(
        TLSResult(checked=True, valid=True, ct_logs_checked=True, ct_first_seen_days_ago=2)
    )

    assert score == 6
    assert reasons == ["Certificate Transparency logs show the domain's first certificate is less than a week old"]


def test_score_tls_does_not_flag_an_established_ct_log_entry() -> None:
    score, reasons = _score_tls(
        TLSResult(checked=True, valid=True, ct_logs_checked=True, ct_first_seen_days_ago=400)
    )

    assert score == 0
    assert reasons == []


def test_score_tls_combines_expired_certificate_and_new_ct_entry() -> None:
    score, reasons = _score_tls(
        TLSResult(checked=True, valid=False, expired=True, ct_logs_checked=True, ct_first_seen_days_ago=1)
    )

    assert score == TLS_SCORE_CAP
    assert reasons == [
        "TLS certificate appears to be expired",
        "Certificate Transparency logs show the domain's first certificate is less than a week old",
    ]


@pytest.mark.asyncio
async def test_scoring_combines_url_and_dom_reasons() -> None:
    result = await analyze_url(
        AnalysisRequest(
            url="http://verify-account.example.test/login",
            dom_features=DOMFeatures(
                has_password_field=True,
                num_forms=1,
                external_form_action=True,
                num_iframes=0,
                external_links_ratio=0.1,
                has_hidden_inputs=False,
            ),
        )
    )

    assert result.risk_score >= 35
    assert result.label in {"suspicious", "dangerous"}
    assert "Domain or path contains suspicious keywords" in result.reasons
    assert "Page contains a password field" in result.reasons
    assert {item.category for item in result.risk_breakdown} == {
        "url",
        "dom",
        "threat_intel",
        "tls",
        "domain_age",
        "ml",
    }
    # The raw sum of breakdown scores equals risk_score only when the total is
    # below 100; at or above the cap they diverge because risk_score is clamped.
    raw_sum = sum(item.score for item in result.risk_breakdown)
    assert result.risk_score == max(0, min(100, raw_sum))


def test_scoring_caps_are_enforced() -> None:
    url_score, _ = _score_url(
        URLFeatures(
            url_length=220,
            num_dots=8,
            num_hyphens=5,
            uses_ip_domain=True,
            has_at_symbol=True,
            uses_https=False,
            num_subdomains=5,
            suspicious_keywords=("login", "verify", "account", "secure"),
            uses_punycode=True,
            domain_entropy=4.5,
            domain="xn--secure-login.example.test",
            typosquat_target=None,
            typosquat_distance=None,
            typosquat_is_homograph=False,
            mixed_script_label=False,
        )
    )
    dom_score, _ = _score_dom(
        DOMFeatures(
            has_password_field=True,
            num_forms=20,
            external_form_action=True,
            num_iframes=20,
            external_links_ratio=1.0,
            has_hidden_inputs=True,
            brand_text_mismatch=True,
            favicon_hotlinked_brand=True,
        )
    )
    threat_score, _ = _score_threat_intel(
        PhishTankResult(checked=True, in_database=True, verified=True, valid=True),
        DemoThreatResult(checked=False),
    )
    tls_score, _ = _score_tls(TLSResult(checked=True, valid=False, expired=True))
    domain_age_score, _ = _score_domain_age(DomainAgeResult(checked=True, age_days=1))

    assert url_score == URL_SCORE_CAP
    assert dom_score == DOM_SCORE_CAP
    assert threat_score == THREAT_INTEL_SCORE_CAP
    assert tls_score == TLS_SCORE_CAP
    assert domain_age_score == DOMAIN_AGE_SCORE_CAP


def test_score_dom_brand_text_mismatch_and_favicon_hotlink() -> None:
    score, reasons = _score_dom(
        DOMFeatures(brand_text_mismatch=True, favicon_hotlinked_brand=True)
    )

    assert score == 20
    assert reasons == [
        "Page text references a well-known brand that does not match this domain",
        "Page favicon is hotlinked from a different brand's domain",
    ]


def test_risk_breakdown_preserves_ml_adjustment_bounds() -> None:
    positive_breakdown = _build_risk_breakdown(
        url_score=0,
        url_reasons=[],
        dom_score=0,
        dom_reasons=[],
        threat_score=0,
        threat_reasons=[],
        phishtank_result=PhishTankResult(checked=False),
        demo_threat_result=DemoThreatResult(checked=False),
        tls_result=TLSResult(checked=False),
        tls_score=0,
        tls_reasons=[],
        domain_age_result=DomainAgeResult(checked=False),
        domain_age_score=0,
        domain_age_reasons=[],
        ml_result=MLResult(available=True, probability=0.99, adjustment=200),
        ml_reasons=["Machine learning model increased the estimated risk"],
    )
    negative_breakdown = _build_risk_breakdown(
        url_score=0,
        url_reasons=[],
        dom_score=0,
        dom_reasons=[],
        threat_score=0,
        threat_reasons=[],
        phishtank_result=PhishTankResult(checked=False),
        demo_threat_result=DemoThreatResult(checked=False),
        tls_result=TLSResult(checked=False),
        tls_score=0,
        tls_reasons=[],
        domain_age_result=DomainAgeResult(checked=False),
        domain_age_score=0,
        domain_age_reasons=[],
        ml_result=MLResult(available=True, probability=0.01, adjustment=-200),
        ml_reasons=["Machine learning model reduced the estimated risk"],
    )

    assert positive_breakdown[-1].score == ML_MAX_ADJUSTMENT
    assert positive_breakdown[-1].max_score == ML_MAX_ADJUSTMENT
    assert positive_breakdown[-1].min_score == ML_MIN_ADJUSTMENT
    assert negative_breakdown[-1].score == ML_MIN_ADJUSTMENT
