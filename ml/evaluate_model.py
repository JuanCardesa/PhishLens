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

    version = artifact.get("version", "unknown")
    trained_at = artifact.get("trained_at", "unknown")
    git_hash = artifact.get("git_hash", "unknown")
    print(f"Model version: {version}  |  trained_at: {trained_at}  |  git: {git_hash}")

    cv_scores = artifact.get("cv_scores")
    if cv_scores:
        import statistics

        mean_cv = statistics.mean(cv_scores)
        stdev_cv = statistics.stdev(cv_scores) if len(cv_scores) > 1 else 0.0
        print(f"Stored CV accuracy: {mean_cv:.3f} ± {stdev_cv:.3f} (from {len(cv_scores)} folds)")

    feature_importances: dict[str, float] = artifact.get("feature_importances", {})
    if feature_importances:
        print("\nTop feature importances (from training artifact):")
        for feat, imp in sorted(feature_importances.items(), key=lambda kv: kv[1], reverse=True)[:5]:
            print(f"  {feat}: {imp:.4f}")

    data = pd.read_csv(DATASET_PATH)
    x = data[feature_order]
    y = data["label"]
    predictions = model.predict(x)

    # Note: this evaluates on the same data used for training because the synthetic dataset
    # is too small for a separate holdout. For production datasets, use train_test_split or
    # cross-validation scores from the stored artifact instead.
    print("\nFull-dataset evaluation (training data — not a held-out test set)")
    print(f"Accuracy: {accuracy_score(y, predictions):.3f}")
    print("Confusion matrix:")
    print(confusion_matrix(y, predictions))
    print("Classification report:")
    print(classification_report(y, predictions, zero_division=0))


if __name__ == "__main__":
    main()
