from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split


ROOT = Path(__file__).resolve().parent
_REAL_DATASET = ROOT / "datasets" / "real_phishing_urls.csv"
_DEMO_DATASET = ROOT / "datasets" / "demo_phishing_urls.csv"
MODEL_PATH = ROOT / "models" / "phishlens_model.joblib"

# Prefer the real dataset built by ml/datasets/build_dataset.py; fall back to
# the synthetic demo set so the pipeline stays runnable without internet access.
DATASET_PATH, _DATASET_IS_REAL = (
    (_REAL_DATASET, True) if _REAL_DATASET.exists() else (_DEMO_DATASET, False)
)
MODEL_VERSION = "0.3.0-real" if _DATASET_IS_REAL else "0.2.0-synthetic"

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


def _git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> None:
    dataset_label = "real (PhishTank + Tranco)" if _DATASET_IS_REAL else "synthetic demo"
    print(f"Dataset: {DATASET_PATH.name} [{dataset_label}]")

    data = pd.read_csv(DATASET_PATH)
    if len(data) < 20:
        raise SystemExit(
            f"Dataset too small ({len(data)} rows). Run `python ml/datasets/build_dataset.py` "
            "to download a real dataset, or add more rows to the synthetic CSV."
        )

    x = data[FEATURE_COLUMNS]
    y = data["label"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.33,
        random_state=42,
        stratify=y,
    )

    baseline = LogisticRegression(max_iter=1000, class_weight="balanced")
    baseline.fit(x_train, y_train)

    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=5,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)

    # k-fold CV on the full dataset gives a more stable performance estimate than
    # a single hold-out split, especially on small datasets.
    n_splits = min(5, int(y.value_counts().min()))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, x, y, cv=cv, scoring="accuracy")
    print(f"Stratified {n_splits}-fold CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    predictions = model.predict(x_test)
    print("\nRandomForest hold-out evaluation")
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions))
    print("Classification report:")
    print(classification_report(y_test, predictions, zero_division=0))

    feature_importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
    print("\nTop feature importances:")
    for feat, imp in sorted(feature_importances.items(), key=lambda kv: kv[1], reverse=True)[:5]:
        print(f"  {feat}: {imp:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "baseline_model": baseline,
            "feature_order": FEATURE_COLUMNS,
            "dataset_note": f"{dataset_label} dataset. DOM features are 0 for URL-only rows.",
            "version": MODEL_VERSION,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "git_hash": _git_hash(),
            "cv_scores": cv_scores.tolist(),
            "feature_importances": feature_importances,
        },
        MODEL_PATH,
    )
    print(f"\nSaved model v{MODEL_VERSION} to {MODEL_PATH}")


if __name__ == "__main__":
    main()
