import pytest

from app.schemas.analysis import AnalysisRequest, ReportRequest
from app.services.url_normalizer import URLNormalizationError, normalize_url


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


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/path",
        "http://127.0.0.1:8080/path",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://172.16.0.1/internal",
        "http://[::1]/ipv6-loopback",
        "http://169.254.0.1/link-local",
    ],
)
def test_normalize_url_rejects_private_ip_literals(url: str) -> None:
    with pytest.raises(URLNormalizationError, match="private or loopback"):
        normalize_url(url)


def test_normalize_url_allows_public_ip() -> None:
    assert normalize_url("https://8.8.8.8/dns") == "https://8.8.8.8/dns"


def test_normalize_url_allows_hostname_that_resolves_privately() -> None:
    # Hostnames like 'localhost' are NOT rejected — only IP literals are blocked.
    # DNS-based SSRF is an accepted risk documented in docs/threat-model.md.
    assert normalize_url("http://localhost/page") == "http://localhost/page"


def test_normalize_url_preserves_public_ipv6_literal_brackets() -> None:
    assert normalize_url("https://[2606:4700:4700::1111]/dns-query") == "https://[2606:4700:4700::1111]/dns-query"


def test_normalize_url_rejects_ipv6_loopback_and_unique_local() -> None:
    for url in ("http://[::1]/", "http://[fc00::1]/"):
        with pytest.raises(URLNormalizationError, match="private or loopback"):
            normalize_url(url)


def test_normalize_url_rejects_shared_address_space() -> None:
    # 100.64.0.0/10 is the CGNAT range (RFC 6598) — not globally routable.
    with pytest.raises(URLNormalizationError, match="private or loopback"):
        normalize_url("http://100.64.0.1/")


def test_normalize_url_rejects_invalid_port() -> None:
    with pytest.raises(URLNormalizationError, match="valid port"):
        normalize_url("http://example.test:99999/")
