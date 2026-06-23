"""Temporal validation: train on older phishing URLs, test on newer ones.

The dataset committed at ml/datasets/real_phishing_urls.csv is validated with k-fold
CV and a random hold-out split (see train_model.py / ml-methodology.md), which only
proves the model generalizes within one snapshot. This script answers a different,
harder question: does a model trained on OLDER phishing campaigns still detect
NEWER ones it has never seen?

PhishTank's public dump includes a `submission_time` per URL, which gives a genuine
time axis on the phishing side. Tranco (legitimate domains) has no time axis — it's
always "current rank now" — so the legitimate side is split by disjoint rank windows
instead of dates. This is a real, documented limitation, not disguised as "temporal".

This script is read-only with respect to the committed dataset and the production
model artifact: it trains and evaluates a separate, throwaway RandomForestClassifier
purely for this validation exercise.

Usage:
    cd ml
    python evaluate_temporal_drift.py
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import logging
import random
import sys
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

TRAIN_OLDER_THAN_DAYS = 365 * 2
TEST_NEWER_THAN_DAYS = 14
SAMPLE_SIZE = 300
TRAIN_LEGIT_TOP_K = 50_000
TEST_LEGIT_RANK_WINDOW = (50_001, 100_000)


def _load_dataset_builder() -> ModuleType:
    module_path = ROOT / "datasets" / "build_dataset.py"
    spec = importlib.util.spec_from_file_location("phishlens_build_dataset", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fetch_phishtank_with_time(dump_url: str) -> list[tuple[str, datetime]]:
    logger.info("Downloading full PhishTank dump for temporal split...")
    with urllib.request.urlopen(dump_url, timeout=60) as resp:
        raw = resp.read()
    with gzip.open(io.BytesIO(raw)) as gz:
        text = gz.read().decode("utf-8", errors="replace")

    entries: list[tuple[str, datetime]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row.get("verified", "").lower() != "yes":
            continue
        url = row.get("url", "").strip()
        submitted = row.get("submission_time", "").strip()
        if not url.startswith(("http://", "https://")) or not submitted:
            continue
        try:
            submitted_at = datetime.fromisoformat(submitted)
        except ValueError:
            continue
        entries.append((url, submitted_at))

    logger.info("PhishTank: %d verified URLs with a parseable submission_time", len(entries))
    return entries


def _fetch_tranco_window(list_url: str, low_rank: int, high_rank: int) -> list[str]:
    logger.info("Downloading Tranco list for rank window [%d, %d]...", low_rank, high_rank)
    with urllib.request.urlopen(list_url, timeout=60) as resp:
        raw = resp.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        csv_name = next(name for name in archive.namelist() if name.endswith(".csv"))
        text = archive.read(csv_name).decode("utf-8", errors="replace")

    domains: list[str] = []
    for line in text.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) != 2:
            continue
        rank_str, domain = parts
        try:
            rank = int(rank_str)
        except ValueError:
            continue
        if rank > high_rank:
            break
        if rank < low_rank:
            continue
        domain = domain.strip().lower()
        if domain and "." in domain:
            domains.append(f"https://{domain}/")

    logger.info("Tranco: %d domains in rank window [%d, %d]", len(domains), low_rank, high_rank)
    return domains


def main() -> int:
    builder = _load_dataset_builder()
    feature_columns = builder.FEATURE_COLUMNS[:-1]  # drop "label"

    now = datetime.now(timezone.utc)
    train_cutoff = now - timedelta(days=TRAIN_OLDER_THAN_DAYS)
    test_cutoff = now - timedelta(days=TEST_NEWER_THAN_DAYS)
    print(f"TRAIN-old cutoff:  submission_time < {train_cutoff.date().isoformat()}")
    print(f"TEST-new cutoff:   submission_time > {test_cutoff.date().isoformat()}")

    phishing_entries = _fetch_phishtank_with_time(builder.PHISHTANK_DUMP_URL)
    older = [url for url, ts in phishing_entries if ts < train_cutoff]
    newer = [url for url, ts in phishing_entries if ts > test_cutoff]
    print(f"Phishing pool: {len(older)} older than cutoff, {len(newer)} newer than cutoff")

    rng = random.Random(42)
    train_phishing = rng.sample(older, min(SAMPLE_SIZE, len(older)))
    test_phishing = rng.sample(newer, min(SAMPLE_SIZE, len(newer)))

    train_legit_raw = builder.fetch_tranco_urls(SAMPLE_SIZE, TRAIN_LEGIT_TOP_K)
    test_legit_raw = _fetch_tranco_window(
        builder.TRANCO_LIST_URL, TEST_LEGIT_RANK_WINDOW[0], TEST_LEGIT_RANK_WINDOW[1]
    )
    test_legit_raw = rng.sample(test_legit_raw, min(SAMPLE_SIZE, len(test_legit_raw)))

    path_rng = random.Random(42)
    train_legit = [builder._add_realistic_path(url, path_rng) for url in train_legit_raw]
    test_legit = [builder._add_realistic_path(url, path_rng) for url in test_legit_raw]

    if not train_phishing or not test_phishing or not train_legit or not test_legit:
        logger.error("Temporal validation aborted — one of the sample pools was empty.")
        return 1

    def to_rows(urls: list[str], label: int) -> list[dict]:
        rows = [builder.extract_url_features(url, label=label) for url in urls]
        return [row for row in rows if row is not None]

    train_rows = to_rows(train_phishing, 1) + to_rows(train_legit, 0)
    test_rows = to_rows(test_phishing, 1) + to_rows(test_legit, 0)

    x_train = [[row[col] for col in feature_columns] for row in train_rows]
    y_train = [row["label"] for row in train_rows]
    x_test = [[row[col] for col in feature_columns] for row in test_rows]
    y_test = [row["label"] for row in test_rows]

    print(f"\nTrain set: {len(x_train)} rows ({sum(y_train)} phishing, {len(y_train) - sum(y_train)} legit)")
    print(f"Test set:  {len(x_test)} rows ({sum(y_test)} phishing, {len(y_test) - sum(y_test)} legit)")

    model = RandomForestClassifier(n_estimators=120, max_depth=5, random_state=42, class_weight="balanced")
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    print("\nTemporal hold-out evaluation (train on older phishing, test on newer)")
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions))
    print("Classification report:")
    print(classification_report(y_test, predictions, zero_division=0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
