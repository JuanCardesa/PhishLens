"""Reliability diagram for the heuristic-only "confidence" formula (no ML).

scoring_service._confidence() falls back to `0.55 + abs(score - 50) / 100`
(capped at 0.9) whenever the ML model is unavailable. That formula was never
claimed to be a calibrated probability — it is a linear proxy for "how far
from the middle of the score range is this result" — but a portfolio review
correctly asked: how far off IS it from a calibrated probability in practice?
This script answers that with real data instead of leaving it as an assertion.

Methodology and its limits, stated plainly:

- Uses the same committed `real_phishing_urls.csv` as `evaluate_heuristics.py`
  and inherits the same constraint: the CSV does not store raw domains (a
  deliberate privacy decision, see docs/ml-methodology.md), so typosquatting/
  homograph/mixed-script URL signals are NOT reconstructable here, and DOM
  features are hardcoded to 0 for every row (no live browser session at
  dataset-build time — see the "Train/inference feature mismatch" section of
  docs/ml-methodology.md for why that matters). The local score computed here
  is therefore a lower bound on what the heuristic engine can detect, not its
  full ceiling.
- The 0-100 score this script feeds into `_confidence()` is scaled the same
  way the extension's offline fallback scales it (see `risk-score.ts`'s
  `LOCAL_MAX_SCORE`): (url_score + dom_score) / (URL_SCORE_CAP + DOM_SCORE_CAP).
  With dom_score always 0 here, this is really just url_score rescaled.
- "Correct" is defined as a binary collapse of the 3-way label: a result is
  "flagged" if label_from_score(score) != "safe" (suspicious or dangerous both
  count), compared against the dataset's ground-truth phishing/legitimate bit.
  This loses the safe/suspicious/dangerous distinction but is the only
  apples-to-apples way to score calibration against a binary ground truth.

Usage:
    cd ml
    python evaluate_confidence_calibration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.feature_extractor import URLFeatures  # noqa: E402
from app.services.ml_service import MLResult  # noqa: E402
from app.services.scoring_service import (  # noqa: E402
    DOM_SCORE_CAP,
    URL_SCORE_CAP,
    _confidence,
    _score_url,
    label_from_score,
)

DATASET_PATH = ROOT / "datasets" / "real_phishing_urls.csv"
OUTPUT_PATH = ROOT / "calibration_reliability_diagram.png"
LOCAL_MAX_SCORE = URL_SCORE_CAP + DOM_SCORE_CAP
BIN_WIDTH = 0.05
NO_ML_RESULT = MLResult(available=False)


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


def _scaled_local_score(url_score: int) -> int:
    # dom_score is always 0 (see module docstring); mirrors risk-score.ts's
    # LOCAL_MAX_SCORE scaling so label_from_score's 35/70 thresholds behave
    # the same way they do for the extension's offline fallback.
    scaled = round((url_score + 0) / LOCAL_MAX_SCORE * 100)
    return max(0, min(100, scaled))


def main() -> None:
    if not DATASET_PATH.exists():
        raise SystemExit(f"{DATASET_PATH} not found. Run `python datasets/build_dataset.py` first.")

    data = pd.read_csv(DATASET_PATH)
    url_scores = [_score_url(_row_to_url_features(row))[0] for _, row in data.iterrows()]
    scaled_scores = [_scaled_local_score(score) for score in url_scores]
    confidences = [_confidence(score, NO_ML_RESULT) for score in scaled_scores]
    flagged = [label_from_score(score) != "safe" for score in scaled_scores]
    correct = [is_flagged == bool(label) for is_flagged, label in zip(flagged, data["label"], strict=True)]

    data = data.assign(confidence=confidences, correct=correct)

    print(f"Calibrating the heuristic-only confidence formula against {len(data)} rows from {DATASET_PATH.name}")
    print(
        "NOTE: url-only score (no DOM/TLS/domain-age/threat-intel/ML), scaled the same way the "
        "extension's offline fallback scales it. See the module docstring for the full caveat.\n"
    )

    bin_starts = [round(0.55 + i * BIN_WIDTH, 2) for i in range(int((0.99 - 0.55) / BIN_WIDTH) + 1)]
    bin_centers: list[float] = []
    bin_accuracies: list[float] = []
    bin_counts: list[int] = []

    print(f"{'confidence bin':>16} | {'mean confidence':>15} | {'empirical accuracy':>19} | {'n':>6}")
    for start in bin_starts:
        end = start + BIN_WIDTH
        # Compare in integer cents, not floats: confidence values are rounded to
        # 2 decimals and the heuristic-only formula is hard-capped at 0.9, so
        # many rows land exactly on a bin boundary (e.g. confidence == 0.90).
        # `start + BIN_WIDTH` is not always exactly representable in float64
        # (e.g. 0.65 + 0.05 can land a hair above 0.70), which silently
        # double-counts boundary rows into both the bin below and the bin they
        # actually belong to if compared as floats.
        start_cents, end_cents = round(start * 100), round(end * 100)
        confidence_cents = (data["confidence"] * 100).round().astype(int)
        in_bin = data[(confidence_cents >= start_cents) & (confidence_cents < end_cents)]
        if in_bin.empty:
            continue

        mean_confidence = in_bin["confidence"].mean()
        accuracy = in_bin["correct"].mean()
        bin_centers.append(mean_confidence)
        bin_accuracies.append(accuracy)
        bin_counts.append(len(in_bin))
        print(f"[{start:.2f}, {end:.2f}) | {mean_confidence:>15.3f} | {accuracy:>19.3f} | {len(in_bin):>6}")

    total = sum(bin_counts)
    mean_calibration_error = sum(
        abs(conf - acc) * count for conf, acc, count in zip(bin_centers, bin_accuracies, bin_counts, strict=True)
    ) / total
    print(f"\nMean calibration error (weighted |confidence - accuracy| across bins): {mean_calibration_error:.3f}")

    _plot_reliability_diagram(bin_centers, bin_accuracies, bin_counts)
    print(f"Reliability diagram written to {OUTPUT_PATH}")


def _plot_reliability_diagram(bin_centers: list[float], bin_accuracies: list[float], bin_counts: list[int]) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0.5, 1.0], [0.5, 1.0], linestyle="--", color="gray", label="Perfectly calibrated")
    sizes = [20 + count for count in bin_counts]
    ax.scatter(bin_centers, bin_accuracies, s=sizes, color="#b42318", label="Heuristic-only confidence (no ML)")
    ax.plot(bin_centers, bin_accuracies, color="#b42318", alpha=0.5)
    ax.set_xlabel("Predicted confidence")
    ax.set_ylabel("Empirical accuracy (flagged matches ground truth)")
    ax.set_title("Reliability diagram: heuristic-only confidence vs. real accuracy")
    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
