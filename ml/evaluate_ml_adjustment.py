"""How much evidence each ML adjustment carries, per probability band.

The backend turns the model's phishing probability into score points with
backend/app/services/ml_service.py::_adjustment_from_probability. Those points
should match what the probability actually tells us. For each probability band,
this script reports the share of legitimate and phishing URLs that land in it,
the likelihood ratio (phishing share / legitimate share: how many times more
likely the band is on phishing), and the adjustment the backend applies there.

It measures two settings:

  * CV       - out-of-fold predictions on the committed dataset (no network).
  * TEMPORAL - a model trained on phishing more than two years old, scored on
               phishing from the last 14 days (--temporal; downloads PhishTank and
               Tranco, same split as evaluate_temporal_drift.py).

TEMPORAL is the one that describes deployment: campaigns the model has never
seen. CV overstates the evidence at both ends, most at the low end (a likelihood
ratio of 0.04 in CV was 0.42 on new phishing), which is why the adjustment is
sized to the temporal numbers. See docs/ml-methodology.md.

Usage:
    cd ml
    python evaluate_ml_adjustment.py [--temporal]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from evaluate_temporal_drift import (
    _load_dataset_builder,
    build_temporal_split,
    make_model,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app.services.ml_service import _adjustment_from_probability  # noqa: E402

DATASET_PATH = ROOT / "datasets" / "real_phishing_urls.csv"

# Bands finer than the shipped mapping, so the table shows why bands were merged.
BANDS = [
    ("p <= 0.20", lambda p: p <= 0.20),
    ("0.20 < p <= 0.35", lambda p: 0.20 < p <= 0.35),
    ("0.35 < p < 0.65", lambda p: 0.35 < p < 0.65),
    ("0.65 <= p < 0.85", lambda p: 0.65 <= p < 0.85),
    ("p >= 0.85", lambda p: p >= 0.85),
]
BAND_MIDPOINTS = [0.10, 0.30, 0.50, 0.75, 0.90]


def report(tag: str, probabilities: np.ndarray, labels: np.ndarray) -> None:
    legit = probabilities[labels == 0]
    phishing = probabilities[labels == 1]
    print(f"\n=== {tag} (n = {len(legit)} legitimate, {len(phishing)} phishing) ===")
    print(f"{'probability band':18} {'legit %':>8} {'phish %':>8} {'LR':>7} {'adjustment':>11}")
    for (name, in_band), midpoint in zip(BANDS, BAND_MIDPOINTS):
        legit_share = float(np.mean([in_band(p) for p in legit]))
        phishing_share = float(np.mean([in_band(p) for p in phishing]))
        ratio = f"{phishing_share / legit_share:7.2f}" if legit_share else "    inf"
        adjustment = _adjustment_from_probability(midpoint)
        print(f"{name:18} {legit_share * 100:8.1f} {phishing_share * 100:8.1f} {ratio} {adjustment:+11d}")

    legit_raised = float(np.mean([_adjustment_from_probability(p) > 0 for p in legit]))
    phishing_lowered = float(np.mean([_adjustment_from_probability(p) < 0 for p in phishing]))
    print(f"legitimate URLs the ML raises: {legit_raised:.1%}   phishing URLs it lowers: {phishing_lowered:.1%}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--temporal", action="store_true", help="also run the temporal split (downloads data)")
    args = parser.parse_args()

    builder = _load_dataset_builder()
    feature_columns = builder.FEATURE_COLUMNS[:-1]
    data = pd.read_csv(DATASET_PATH)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_probabilities = cross_val_predict(
        make_model(), data[feature_columns], data["label"], cv=cv, method="predict_proba"
    )[:, 1]
    report("CV out-of-fold, committed dataset", cv_probabilities, data["label"].to_numpy())

    if args.temporal:
        split = build_temporal_split(builder)
        if split is None:
            return 1
        x_train, y_train, x_test, y_test = split
        model = make_model().fit(x_train, y_train)
        temporal_probabilities = model.predict_proba(x_test)[:, 1]
        report("TEMPORAL: trained on old phishing, scored on new", temporal_probabilities, np.array(y_test))

    return 0


if __name__ == "__main__":
    sys.exit(main())
