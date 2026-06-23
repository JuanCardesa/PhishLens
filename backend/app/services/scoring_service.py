from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSources,
    DOMFeatures,
    RiskBreakdownItem,
    RiskLabel,
)
from app.services.demo_threat_service import DemoThreatResult, check_demo_threat_source
from app.services.feature_extractor import URLFeatures, extract_url_features
from app.services.ml_service import MLResult, predict_ml_adjustment
from app.services.phishtank_service import PhishTankResult, check_url
from app.services.tls_service import TLSResult, inspect_tls

logger = logging.getLogger(__name__)


URL_SCORE_CAP = 35
DOM_SCORE_CAP = 30
THREAT_INTEL_SCORE_CAP = 40
TLS_SCORE_CAP = 15
ML_MIN_ADJUSTMENT = -10
ML_MAX_ADJUSTMENT = 20


def label_from_score(score: int) -> RiskLabel:
    if score >= 70:
        return "dangerous"
    if score >= 35:
        return "suspicious"
    return "safe"


async def analyze_url(request: AnalysisRequest) -> AnalysisResponse:
    settings = get_settings()
    url_features = extract_url_features(request.url)
    demo_threat_result = check_demo_threat_source(request.url)

    # Each service has its own per-request timeout; this outer guard prevents both
    # running in sequence from exceeding a combined wall-clock budget.
    gather_timeout = settings.external_timeout_seconds * 2.5
    try:
        phishtank_result, tls_result = await asyncio.wait_for(
            asyncio.gather(check_url(request.url), inspect_tls(request.url)),
            timeout=gather_timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("external_services_timeout", extra={"timeout_seconds": gather_timeout})
        phishtank_result = PhishTankResult(checked=False, in_database=False, verified=False, valid=False)
        tls_result = TLSResult(checked=False)

    ml_result = predict_ml_adjustment(url_features, request.dom_features)

    url_score, url_reasons = _score_url(url_features)
    dom_score, dom_reasons = _score_dom(request.dom_features)
    threat_score, threat_reasons = _score_threat_intel(phishtank_result, demo_threat_result)
    tls_score, tls_reasons = _score_tls(tls_result)
    ml_reasons = _ml_reasons(ml_result)

    raw_score = url_score + dom_score + threat_score + tls_score + ml_result.adjustment
    risk_score = max(0, min(100, round(raw_score)))
    risk_breakdown = _build_risk_breakdown(
        url_score=url_score,
        url_reasons=url_reasons,
        dom_score=dom_score,
        dom_reasons=dom_reasons,
        threat_score=threat_score,
        threat_reasons=threat_reasons,
        phishtank_result=phishtank_result,
        demo_threat_result=demo_threat_result,
        tls_result=tls_result,
        tls_score=tls_score,
        tls_reasons=tls_reasons,
        ml_result=ml_result,
        ml_reasons=ml_reasons,
    )
    reasons = url_reasons + dom_reasons + threat_reasons + tls_reasons + ml_reasons

    if not reasons:
        reasons = ["No high-risk signals were detected"]

    return AnalysisResponse(
        risk_score=risk_score,
        label=label_from_score(risk_score),
        confidence=_confidence(risk_score, ml_result),
        reasons=reasons,
        sources=AnalysisSources(
            heuristics=True,
            ml=ml_result.available,
            phishtank=phishtank_result.checked,
            tls=tls_result.checked,
            demo=demo_threat_result.matched,
        ),
        risk_breakdown=risk_breakdown,
    )


def _score_url(features: URLFeatures) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if features.url_length > 120:
        score += 12
        reasons.append("URL is unusually long")
    elif features.url_length > 75:
        score += 7
        reasons.append("URL is longer than typical")

    if features.num_dots > 4:
        score += 6
        reasons.append("URL contains many dots")

    if features.num_hyphens > 2:
        score += 4
        reasons.append("URL contains multiple hyphens")

    if features.uses_ip_domain:
        score += 9
        reasons.append("URL uses an IP address as the domain")

    if features.has_at_symbol:
        score += 8
        reasons.append("URL contains an @ symbol")

    if not features.uses_https:
        score += 5
        reasons.append("URL does not use HTTPS")

    if features.num_subdomains > 2:
        score += 4
        reasons.append("URL contains many subdomains")

    if features.suspicious_keywords:
        score += min(8, 4 * len(features.suspicious_keywords))
        reasons.append("Domain or path contains suspicious keywords")

    if features.typosquat_target:
        if features.typosquat_is_homograph:
            score += 16
            reasons.append(
                f"Domain uses look-alike Unicode characters resembling {features.typosquat_target} "
                "(homograph attack)"
            )
        else:
            score += 14
            reasons.append(f"Domain closely resembles {features.typosquat_target} (possible typosquatting)")

    if features.mixed_script_label:
        score += 8
        reasons.append("Domain label mixes multiple writing scripts (possible homograph attack)")

    if features.domain_entropy > 3.8:
        score += 5
        reasons.append("Domain has high character entropy")

    return min(score, URL_SCORE_CAP), reasons


def _score_dom(features: DOMFeatures) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if features.num_forms > 0:
        score += 4
        reasons.append("Page contains forms")

    if features.has_password_field:
        score += 8
        reasons.append("Page contains a password field")

    if features.external_form_action:
        score += 10
        reasons.append("Form submits data to an external domain")

    if features.num_iframes > 2:
        score += 6
        reasons.append("Page contains multiple iframes")
    elif features.num_iframes > 0:
        score += 3
        reasons.append("Page contains iframes")

    if features.external_links_ratio > 0.5:
        score += 5
        reasons.append("Page has a high ratio of external links")

    if features.has_hidden_inputs:
        score += 4
        reasons.append("Page contains hidden form inputs")

    return min(score, DOM_SCORE_CAP), reasons


def _score_threat_intel(result: PhishTankResult, demo_result: DemoThreatResult) -> tuple[int, list[str]]:
    if demo_result.matched:
        return THREAT_INTEL_SCORE_CAP, ["Local demo threat source is enabled for this walkthrough"]
    if result.in_database and result.verified and result.valid:
        return THREAT_INTEL_SCORE_CAP, ["URL appears in a verified phishing intelligence feed"]
    if result.in_database:
        return 25, ["URL appears in a phishing intelligence feed"]
    return 0, []


def _score_tls(result: TLSResult) -> tuple[int, list[str]]:
    if not result.checked:
        return 0, []

    score = 0
    reasons: list[str] = []

    if result.expired:
        score += 15
        reasons.append("TLS certificate appears to be expired")
    elif result.days_until_expiration is not None and result.days_until_expiration < 14:
        score += 8
        reasons.append("TLS certificate expires soon")
    elif not result.valid:
        score += 10
        reasons.append("TLS certificate could not be validated")

    if result.error and not reasons:
        score += 4
        reasons.append("TLS certificate check returned an error")

    return min(score, TLS_SCORE_CAP), reasons


def _ml_reasons(result: MLResult) -> list[str]:
    if not result.available or result.probability is None or result.adjustment == 0:
        return []

    if result.adjustment > 0:
        return ["Machine learning model increased the estimated risk"]

    return ["Machine learning model reduced the estimated risk"]


def _build_risk_breakdown(
    *,
    url_score: int,
    url_reasons: list[str],
    dom_score: int,
    dom_reasons: list[str],
    threat_score: int,
    threat_reasons: list[str],
    phishtank_result: PhishTankResult,
    demo_threat_result: DemoThreatResult,
    tls_result: TLSResult,
    tls_score: int,
    tls_reasons: list[str],
    ml_result: MLResult,
    ml_reasons: list[str],
) -> list[RiskBreakdownItem]:
    return [
        RiskBreakdownItem(
            category="url",
            score=url_score,
            max_score=URL_SCORE_CAP,
            reasons=url_reasons,
            source="heuristics",
        ),
        RiskBreakdownItem(
            category="dom",
            score=dom_score,
            max_score=DOM_SCORE_CAP,
            reasons=dom_reasons,
            source="dom",
        ),
        RiskBreakdownItem(
            category="threat_intel",
            score=threat_score,
            max_score=THREAT_INTEL_SCORE_CAP,
            reasons=threat_reasons,
            source=_threat_intel_source(phishtank_result, demo_threat_result),
        ),
        RiskBreakdownItem(
            category="tls",
            score=tls_score,
            max_score=TLS_SCORE_CAP,
            reasons=tls_reasons,
            source="tls" if tls_result.checked else "fallback",
        ),
        RiskBreakdownItem(
            category="ml",
            score=max(ML_MIN_ADJUSTMENT, min(ML_MAX_ADJUSTMENT, ml_result.adjustment)),
            min_score=ML_MIN_ADJUSTMENT,
            max_score=ML_MAX_ADJUSTMENT,
            reasons=ml_reasons,
            source="ml" if ml_result.available else "fallback",
        ),
    ]


def _threat_intel_source(result: PhishTankResult, demo_result: DemoThreatResult) -> str:
    if demo_result.matched:
        return "demo"
    if result.checked:
        return "phishtank"
    return "fallback"


def _confidence(score: int, ml_result: MLResult) -> float:
    if ml_result.available and ml_result.probability is not None:
        return round(max(0.55, min(0.99, ml_result.probability)), 2)
    return round(min(0.9, 0.55 + abs(score - 50) / 100), 2)
