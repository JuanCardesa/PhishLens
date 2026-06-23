import pytest

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


def test_extract_url_features_detects_typosquatting_across_tlds() -> None:
    features = extract_url_features("https://paypa1.net/login")

    assert features.typosquat_target == "paypal.com"
    assert features.typosquat_distance == 1


def test_extract_url_features_detects_combosquatting() -> None:
    features = extract_url_features("https://paypal-secure-login.com/account")

    assert features.typosquat_target == "paypal.com"
    assert features.typosquat_distance == 1


def test_extract_url_features_detects_combosquatting_on_two_label_public_suffix() -> None:
    features = extract_url_features("https://paypal-secure.co.uk/account")

    assert features.typosquat_target == "paypal.com"
    assert features.typosquat_distance == 1
    assert features.num_subdomains == 0


def test_extract_url_features_does_not_flag_the_real_brand_domain() -> None:
    features = extract_url_features("https://paypal.com/login")

    assert features.typosquat_target is None
    assert features.typosquat_distance is None


def test_extract_url_features_does_not_flag_exact_brand_label_on_alternate_suffix() -> None:
    features = extract_url_features("https://accounts.google.co.uk/login")

    assert features.typosquat_target is None
    assert features.typosquat_distance is None
    assert features.num_subdomains == 1


@pytest.mark.parametrize(
    "url",
    (
        "https://raw.githubusercontent.com/JuanCardesa/PhishLens/main/README.md",
        "https://storage.googleapis.com/example-bucket/file.txt",
        "https://appleton.com/",
    ),
)
def test_extract_url_features_does_not_flag_brand_substrings_without_separator(url: str) -> None:
    features = extract_url_features(url)

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
    assert features.mixed_script_label is False


def test_extract_url_features_detects_full_script_homograph() -> None:
    # xn--80ak6aa92e decodes to "аррӏе" (all Cyrillic look-alikes of "apple")
    features = extract_url_features("https://xn--80ak6aa92e.com/login")

    assert features.typosquat_target == "apple.com"
    assert features.typosquat_distance == 0
    assert features.typosquat_is_homograph is True
    # A single, consistently Cyrillic label is not "mixed" script.
    assert features.mixed_script_label is False


def test_extract_url_features_detects_mixed_script_homograph() -> None:
    # "gооgle.com": the two "o"s are Cyrillic look-alikes (U+043E).
    features = extract_url_features("https://gооgle.com/login")

    assert features.typosquat_target == "google.com"
    assert features.typosquat_distance == 0
    assert features.typosquat_is_homograph is True
    assert features.mixed_script_label is True


def test_extract_url_features_flags_mixed_script_without_brand_match() -> None:
    # "tеst-аbc.com": Cyrillic "е" and "а" mixed into an otherwise
    # Latin label that does not resemble any known brand.
    features = extract_url_features("https://tеst-аbc.com/")

    assert features.mixed_script_label is True
    assert features.typosquat_target is None
    assert features.typosquat_distance is None
    assert features.typosquat_is_homograph is False


def test_extract_url_features_does_not_flag_ascii_typosquat_as_homograph() -> None:
    features = extract_url_features("https://paypa1.com/login")

    assert features.typosquat_is_homograph is False
    assert features.mixed_script_label is False


def test_extract_url_features_handles_malformed_punycode_without_crashing() -> None:
    features = extract_url_features("https://xn--invalid-punycode-zzzzzzzzzzzzz.com/")

    assert features.typosquat_target is None
    assert features.typosquat_distance is None
