from app.schemas.analysis import AnalysisRequest, ReportRequest
from app.services.url_normalizer import normalize_url


def test_normalize_url_lowercases_scheme_host_and_removes_fragment() -> None:
    assert normalize_url(" HTTPS://Example.TEST/login?next=/home#token ") == "https://example.test/login?next=/home"


def test_normalize_url_strips_userinfo() -> None:
    assert normalize_url("https://user:pass@Example.TEST:8443/login#token") == "https://example.test:8443/login"


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
