from app.schemas.analysis import AnalysisRequest, ReportRequest
from app.services.url_normalizer import URLNormalizationError, normalize_url


def test_normalize_url_lowercases_scheme_host_and_removes_fragment() -> None:
    assert normalize_url(" HTTPS://Example.TEST/login?next=/home#token ") == "https://example.test/login?next=/home"


def test_normalize_url_strips_userinfo() -> None:
    assert normalize_url("https://user:pass@Example.TEST:8443/login#token") == "https://example.test:8443/login"


def test_normalize_url_preserves_public_ipv6_literal() -> None:
    assert normalize_url("https://[2606:4700:4700::1111]/dns-query") == "https://[2606:4700:4700::1111]/dns-query"


def test_normalize_url_rejects_non_global_ip_literals() -> None:
    for value in (
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://100.64.0.1/",
        "http://[::1]/",
        "http://[fc00::1]/",
        "http://203.0.113.10/",
    ):
        try:
            normalize_url(value)
        except URLNormalizationError:
            continue
        raise AssertionError(f"Expected URLNormalizationError for {value}")


def test_analysis_request_normalizes_url() -> None:
    request = AnalysisRequest(url="HTTPS://Example.TEST/login#private", dom_features={})

    assert request.url == "https://example.test/login"


def test_report_request_normalizes_url() -> None:
    request = ReportRequest(
        url="HTTP://Example.TEST/path#private",
        observed_label="safe",
        expected_label="dangerous",
    )

    assert request.url == "http://example.test/path"
