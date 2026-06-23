"""Backtest the rule-based URL scoring weights against the real dataset (no ML).

ml/datasets/real_phishing_urls.csv deliberately does not store raw URLs/domains
(see docs/ml-methodology.md), so this script can only reconstruct the columns that
ARE present: url_length, num_dots, num_hyphens, uses_ip_domain, has_at_symbol,
uses_https, num_subdomains, suspicious_keyword_count, uses_punycode, domain_entropy.

It therefore CANNOT backtest typosquatting/homograph/mixed-script detection, which
require the actual domain string. Treat the numbers below as a partial backtest of
_score_url's non-domain-string-dependent weights, not a full evaluation of the URL
heuristic engine.

Usage:
    cd ml
    python evaluate_heuristics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.feature_extractor import URLFeatures  # noqa: E402
from app.services.scoring_service import URL_SCORE_CAP, _score_url  # noqa: E402

DATASET_PATH = ROOT / "datasets" / "real_phishing_urls.csv"
THRESHOLDS = (1, 8, 14, 20, 30)


def _row_to_url_features(row: "pd.Series[object]") -> URLFeatures:
    keyword_count = int(row["suspicious_keyword_count"])
    return URLFeatures(
        url_length=int(row["url_length"]),
        num_dots=int(row["num_dots"]),
        num_hyphens=int(row["num_hyphens"]),
        uses_ip_domain=bool(row["uses_ip_domain"]),
        has_at_symbol=bool(row["has_at_symbol"]),
        uses_https=bool(row["uses_https"]),
        num_subdomains=int(row["num_subdomains"]),
        suspicious_keywords=tuple(f"kw{i}" for i in range(keyword_count)),
        uses_punycode=bool(row["uses_punycode"]),
        domain_entropy=float(row["domain_entropy"]),
        domain="",
        # Not reconstructable from the CSV — see module docstring.
        typosquat_target=None,
        typosquat_distance=None,
        typosquat_is_homograph=False,
        mixed_script_label=False,
    )


def main() -> None:
    if not DATASET_PATH.exists():
        raise SystemExit(f"{DATASET_PATH} not found. Run `python datasets/build_dataset.py` first.")

    data = pd.read_csv(DATASET_PATH)
    scores = [_score_url(_row_to_url_features(row))[0] for _, row in data.iterrows()]
    data = data.assign(heuristic_score=scores)
    labels = data["label"]

    print(f"Backtesting _score_url against {len(data)} rows from {DATASET_PATH.name}")
    print(
        "NOTE: typosquatting/homograph/mixed-script signals are NOT included — "
        "the committed dataset does not store raw domains (privacy). This only "
        "backtests url_length/dots/hyphens/ip/@/https/subdomains/keywords/punycode/entropy.\n"
    )

    cap_fraction_phishing = (data.loc[labels == 1, "heuristic_score"] >= URL_SCORE_CAP).mean()
    cap_fraction_legit = (data.loc[labels == 0, "heuristic_score"] >= URL_SCORE_CAP).mean()
    print(f"Fraction hitting the {URL_SCORE_CAP}-point cap — phishing: {cap_fraction_phishing:.2%}, legitimate: {cap_fraction_legit:.2%}\n")

    print(f"{'threshold':>9} | {'precision':>9} | {'recall':>9} | {'f1':>9}")
    for threshold in THRESHOLDS:
        predicted = (data["heuristic_score"] >= threshold).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predicted, average="binary", zero_division=0
        )
        print(f"{threshold:>9} | {precision:>9.3f} | {recall:>9.3f} | {f1:>9.3f}")


if __name__ == "__main__":
    main()
