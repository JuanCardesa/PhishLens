"""Stratified k-fold cross-validation with the full phishing metric set.

`train_model.py` prints only CV *accuracy*, which is a weak headline for a
detector: it hides the precision/recall trade-off. This script re-runs the same
model (`RandomForestClassifier`, identical hyperparameters) under stratified
k-fold CV and reports the metrics that actually matter for phishing -
precision, recall, F1, false-positive rate, ROC-AUC, the aggregated confusion
matrix - plus the dataset's class balance.

Phishing is the positive class (label 1).

## Leakage note

The committed CSV stores only the 16 numeric features and a label, never raw
URLs or domains (a deliberate privacy decision, see docs/ml-methodology.md), so
*domain-level* leakage (same host in train and test) cannot be verified from the
file. The closest observable proxy is duplicate feature vectors: PhishTank
captures many paths on one host and Tranco roots collapse to the same numeric
row, so identical vectors can land in both the train and test folds of a random
split. This script quantifies those duplicates and reports metrics twice:

  * AS-IS       - the dataset exactly as committed (matches train_model.py).
  * DEDUPLICATED - one row per distinct feature vector, which removes the
                   random-fold leakage vector.

On the committed snapshot the deduplicated numbers are *higher*, not lower, so
the duplicates are conservative rather than inflationary - the headline accuracy
is not propped up by leakage. The deduplicated figures are the cleaner
generalization estimate; both are printed for transparency.

Usage:
    cd ml
    python evaluate_cv_metrics.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parent
_REAL_DATASET = ROOT / "datasets" / "real_phishing_urls.csv"
_DEMO_DATASET = ROOT / "datasets" / "demo_phishing_urls.csv"

DATASET_PATH, _DATASET_IS_REAL = (
    (_REAL_DATASET, True) if _REAL_DATASET.exists() else (_DEMO_DATASET, False)
)

# Kept in sync with train_model.py::FEATURE_COLUMNS.
FEATURE_COLUMNS = [
    "url_length",
    "num_dots",
    "num_hyphens",
    "uses_ip_domain",
    "has_at_symbol",
    "uses_https",
    "num_subdomains",
    "suspicious_keyword_count",
    "uses_punycode",
    "domain_entropy",
    "has_password_field",
    "num_forms",
    "external_form_action",
    "num_iframes",
    "external_links_ratio",
    "has_hidden_inputs",
]

N_SPLITS = 5
RANDOM_STATE = 42


def _make_model() -> RandomForestClassifier:
    # Identical to train_model.py so these metrics describe the shipped model.
    return RandomForestClassifier(
        n_estimators=120,
        max_depth=5,
        random_state=RANDOM_STATE,
        class_weight="balanced",
    )


@dataclass
class CVMetrics:
    tag: str
    n: int
    n_phishing: int
    n_legit: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    fpr: float
    roc_auc: float
    tn: int
    fp: int
    fn: int
    tp: int
    fold_f1_mean: float
    fold_f1_std: float


def evaluate(df: pd.DataFrame, tag: str) -> CVMetrics:
    x = df[FEATURE_COLUMNS]
    y = df["label"].to_numpy()

    n_splits = min(N_SPLITS, int(pd.Series(y).value_counts().min()))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)

    # cross_val_predict yields an out-of-fold prediction for every row exactly
    # once, so the confusion matrix below is a true aggregate across all folds,
    # not an average of per-fold matrices.
    pred = cross_val_predict(_make_model(), x, y, cv=cv)
    proba = cross_val_predict(_make_model(), x, y, cv=cv, method="predict_proba")[:, 1]

    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    fold_f1 = []
    for train_idx, test_idx in cv.split(x, y):
        model = _make_model()
        model.fit(x.iloc[train_idx], y[train_idx])
        fold_f1.append(f1_score(y[test_idx], model.predict(x.iloc[test_idx])))

    return CVMetrics(
        tag=tag,
        n=len(df),
        n_phishing=int((y == 1).sum()),
        n_legit=int((y == 0).sum()),
        accuracy=accuracy_score(y, pred),
        precision=precision_score(y, pred, zero_division=0),
        recall=recall_score(y, pred, zero_division=0),
        f1=f1_score(y, pred, zero_division=0),
        fpr=fp / (fp + tn) if (fp + tn) else 0.0,
        roc_auc=roc_auc_score(y, proba),
        tn=int(tn),
        fp=int(fp),
        fn=int(fn),
        tp=int(tp),
        fold_f1_mean=float(np.mean(fold_f1)),
        fold_f1_std=float(np.std(fold_f1)),
    )


def _print(m: CVMetrics) -> None:
    print(f"\n=== {m.tag} ===")
    print(f"N = {m.n}   class balance: {m.n_phishing} phishing / {m.n_legit} legitimate "
          f"({m.n_phishing / m.n:.1%} positive)")
    print(f"accuracy   {m.accuracy:.4f}")
    print(f"precision  {m.precision:.4f}   (phishing = positive class)")
    print(f"recall     {m.recall:.4f}")
    print(f"f1         {m.f1:.4f}")
    print(f"fpr        {m.fpr:.4f}   (legitimate pages wrongly flagged)")
    print(f"roc_auc    {m.roc_auc:.4f}")
    print("aggregated confusion matrix (out-of-fold):")
    print("                  pred legit   pred phishing")
    print(f"  actual legit       {m.tn:>6}        {m.fp:>6}")
    print(f"  actual phishing    {m.fn:>6}        {m.tp:>6}")
    print(f"per-fold F1: mean {m.fold_f1_mean:.4f} +/- {m.fold_f1_std:.4f}")


def main() -> None:
    label = "real (PhishTank + Tranco)" if _DATASET_IS_REAL else "synthetic demo"
    df = pd.read_csv(DATASET_PATH)
    n_dup_rows = int(df.duplicated(keep=False).sum())
    n_unique = int(df[FEATURE_COLUMNS].drop_duplicates().shape[0])

    print(f"Dataset: {DATASET_PATH.name} [{label}]")
    print("Model:   RandomForest(n_estimators=120, max_depth=5, class_weight='balanced')")
    print(f"CV:      Stratified {N_SPLITS}-fold, shuffle, random_state={RANDOM_STATE}")
    print("\nLeakage diagnostic (feature-vector duplicates - domain-level leakage is not")
    print("checkable because the CSV stores no domains, by design):")
    print(f"  fully duplicate rows:    {n_dup_rows}")
    print(f"  unique feature vectors:  {n_unique} of {len(df)}")

    as_is = evaluate(df, "AS-IS (with duplicate feature vectors - matches train_model.py)")
    _print(as_is)

    dedup = df.drop_duplicates(subset=FEATURE_COLUMNS).reset_index(drop=True)
    corrected = evaluate(dedup, "DEDUPLICATED (leakage-corrected: one row per feature vector)")
    _print(corrected)

    print("\n" + "=" * 68)
    print("Headline (honest, conservative - as-is dataset):")
    print(f"  {as_is.precision:.1%} precision / {as_is.recall:.1%} recall "
          f"({N_SPLITS}-fold stratified CV, N={as_is.n:,})")
    print("Leakage-corrected (deduplicated):")
    print(f"  {corrected.precision:.1%} precision / {corrected.recall:.1%} recall "
          f"({N_SPLITS}-fold stratified CV, N={corrected.n:,})")


if __name__ == "__main__":
    main()
