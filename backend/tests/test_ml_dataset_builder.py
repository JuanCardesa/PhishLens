from __future__ import annotations

import importlib.util
from pathlib import Path

from app.schemas.analysis import DOMFeatures
from app.services.feature_extractor import extract_url_features
from app.services.ml_service import _feature_values

REAL_DATASET_PATH = Path(__file__).resolve().parents[2] / "ml" / "datasets" / "real_phishing_urls.csv"


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


def test_real_dataset_url_length_is_not_trivially_separable_by_class() -> None:
    """Regression guard for a dataset bias found during a portfolio audit.

    Tranco only provides bare domains, so legitimate rows were originally built as
    plain domain roots while PhishTank phishing URLs almost always carry a path/query.
    That made `url_length` (and correlated features like num_dots/num_hyphens) nearly
    perfectly separable by class — the model could "detect phishing" just by checking
    whether the URL had a path, which doesn't generalize to real-world phishing hosted
    at a clean root domain or legitimate pages with long URLs. build_dataset.py now
    appends realistic paths to most legitimate URLs (see REALISTIC_PATH_TEMPLATES); this
    test fails if that mitigation regresses.
    """
    if not REAL_DATASET_PATH.exists():
        return

    import pandas as pd

    data = pd.read_csv(REAL_DATASET_PATH)
    legit_lengths = data.loc[data["label"] == 0, "url_length"]
    phishing_lengths = data.loc[data["label"] == 1, "url_length"]

    # A trivial-separability regression looks like nearly every legitimate URL being
    # shorter than nearly every phishing URL. Require real overlap between the two
    # distributions instead.
    assert legit_lengths.quantile(0.75) > phishing_lengths.quantile(0.25), (
        "Legitimate and phishing url_length distributions no longer overlap — "
        "the dataset may have regressed to bare-root legitimate URLs."
    )
    assert legit_lengths.mean() > 25, (
        "Legitimate URLs are suspiciously short on average — "
        "REALISTIC_PATH_TEMPLATES may not be applied."
    )
