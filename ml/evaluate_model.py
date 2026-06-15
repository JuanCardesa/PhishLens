from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "demo_phishing_urls.csv"
MODEL_PATH = ROOT / "models" / "phishlens_model.joblib"


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit("Model artifact not found. Run `python ml/train_model.py` first.")

    artifact = joblib.load(MODEL_PATH)
    model = artifact["model"]
    feature_order = artifact["feature_order"]
    data = pd.read_csv(DATASET_PATH)
    x = data[feature_order]
    y = data["label"]
    predictions = model.predict(x)

    print("Demo dataset evaluation")
    print(f"Accuracy: {accuracy_score(y, predictions):.3f}")
    print("Confusion matrix:")
    print(confusion_matrix(y, predictions))
    print("Classification report:")
    print(classification_report(y, predictions, zero_division=0))


if __name__ == "__main__":
    main()
