from __future__ import annotations

import importlib.util
from pathlib import Path

from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import extract_url_features
from app.services.ml_service import _feature_values


def _load_dataset_builder():
    module_path = Path(__file__).resolve().parents[2] / "ml" / "datasets" / "build_dataset.py"
    spec = importlib.util.spec_from_file_location("phishlens_build_dataset", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dataset_builder_matches_backend_url_feature_values() -> None:
    builder = _load_dataset_builder()
    urls = [
        "https://paypal-secure.example/login",
        "http://192.0.2.10/account",
        "https://xn--80ak6aa92e.com/",
    ]

    for url in urls:
        row = builder.extract_url_features(url, label=1)
        expected = _feature_values(extract_url_features(url), DOMFeatures())

        assert row is not None
        assert row["label"] == 1
        for column in builder.FEATURE_COLUMNS:
            if column != "label":
                assert row[column] == expected[column]
