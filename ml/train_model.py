from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "demo_phishing_urls.csv"
MODEL_PATH = ROOT / "models" / "phishlens_model.joblib"

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


def main() -> None:
    data = pd.read_csv(DATASET_PATH)
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

    predictions = model.predict(x_test)
    print("RandomForest demo evaluation")
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions))
    print("Classification report:")
    print(classification_report(y_test, predictions, zero_division=0))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "baseline_model": baseline,
            "feature_order": FEATURE_COLUMNS,
            "dataset_note": "Synthetic demo data for pipeline validation only. Not production-ready.",
        },
        MODEL_PATH,
    )
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
