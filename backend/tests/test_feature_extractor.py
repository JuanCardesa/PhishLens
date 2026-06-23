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


def test_extract_url_features_detects_typosquatting_via_levenshtein() -> None:
    features = extract_url_features("https://paypa1.com/login")

    assert features.typosquat_target == "paypal.com"
    assert features.typosquat_distance == 1


def test_extract_url_features_detects_combosquatting() -> None:
    features = extract_url_features("https://paypal-secure-login.com/account")

    assert features.typosquat_target == "paypal.com"
    assert features.typosquat_distance == 1


def test_extract_url_features_does_not_flag_the_real_brand_domain() -> None:
    features = extract_url_features("https://paypal.com/login")

    assert features.typosquat_target is None
    assert features.typosquat_distance is None


def test_extract_url_features_does_not_flag_unrelated_domains() -> None:
    features = extract_url_features("https://example.com")

    assert features.typosquat_target is None
    assert features.typosquat_distance is None


def test_extract_url_features_skips_typosquat_check_for_ip_domains() -> None:
    features = extract_url_features("http://192.168.0.1/login")

    assert features.typosquat_target is None
    assert features.typosquat_distance is None
