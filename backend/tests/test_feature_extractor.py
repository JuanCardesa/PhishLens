from app.services.feature_extractor import extract_url_features


def test_extract_url_features_detects_suspicious_signals() -> None:
    features = extract_url_features("http://secure-login.example.com.verify.test/account-update")

    assert features.url_length > 0
    assert features.uses_https is False
    assert features.num_subdomains >= 3
    assert "login" in features.suspicious_keywords
    assert "secure" in features.suspicious_keywords
    assert "account" in features.suspicious_keywords
    assert "update" in features.suspicious_keywords


def test_extract_url_features_detects_ip_and_at_symbol() -> None:
    features = extract_url_features("https://user@example.com@192.168.0.1/login")

    assert features.uses_ip_domain is True
    assert features.has_at_symbol is True
    assert features.domain == "192.168.0.1"
