import json

from app.services.brand_domains import _SEED_BRAND_DOMAINS, load_brand_domains


def test_default_path_loads_the_committed_seed_file() -> None:
    domains = load_brand_domains()

    assert "paypal.com" in domains
    assert "google.com" in domains
    assert len(domains) == 26


def test_custom_path_overrides_the_seed_list(tmp_path) -> None:
    custom_file = tmp_path / "custom_brands.json"
    custom_file.write_text(json.dumps(["examplebank.com", "examplepay.com"]), encoding="utf-8")

    domains = load_brand_domains(custom_file)

    assert domains == ("examplebank.com", "examplepay.com")


def test_missing_file_falls_back_to_the_builtin_seed(tmp_path) -> None:
    missing_file = tmp_path / "does-not-exist.json"

    domains = load_brand_domains(missing_file)

    assert domains == _SEED_BRAND_DOMAINS


def test_malformed_json_falls_back_to_the_builtin_seed(tmp_path) -> None:
    malformed_file = tmp_path / "malformed.json"
    malformed_file.write_text("{not valid json", encoding="utf-8")

    domains = load_brand_domains(malformed_file)

    assert domains == _SEED_BRAND_DOMAINS


def test_invalid_shape_falls_back_to_the_builtin_seed(tmp_path) -> None:
    wrong_shape_file = tmp_path / "wrong_shape.json"
    wrong_shape_file.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    domains = load_brand_domains(wrong_shape_file)

    assert domains == _SEED_BRAND_DOMAINS


def test_empty_list_falls_back_to_the_builtin_seed(tmp_path) -> None:
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("[]", encoding="utf-8")

    domains = load_brand_domains(empty_file)

    assert domains == _SEED_BRAND_DOMAINS
