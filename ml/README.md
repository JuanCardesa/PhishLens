# PhishLens ML

This folder contains the first machine learning pipeline for PhishLens.

`datasets/real_phishing_urls.csv` is the preferred committed training dataset. It contains only numeric features and labels. `datasets/demo_phishing_urls.csv` remains as a small offline fallback for validating the training and inference flow.

## Train

```bash
python ml/train_model.py
```

The script trains a Logistic Regression baseline and a RandomForestClassifier, writes the selected model to `ml/models/phishlens_model.joblib`, and copies the runtime artifact to `backend/app/models/phishlens_model.joblib` so the backend image includes the trained model.

## Evaluate

```bash
python ml/evaluate_model.py       # re-checks the saved artifact on its training distribution
python ml/evaluate_cv_metrics.py  # full 5-fold CV metric set (precision/recall/F1/FPR/ROC-AUC)
python ml/evaluate_ml_adjustment.py --temporal  # evidence per probability band vs. the score adjustment
```

`evaluate_model.py` validates the saved artifact's dataset name and SHA-256 before reporting metrics, so stale local models fail fast instead of being evaluated against the wrong CSV.

`evaluate_cv_metrics.py` re-runs the shipped model under stratified 5-fold cross-validation and reports precision, recall, F1, false-positive rate, ROC-AUC, the aggregated out-of-fold confusion matrix, and the class balance — the metrics that actually matter for phishing, which `train_model.py`'s accuracy-only CV line hides. It also quantifies duplicate feature vectors (the closest observable proxy for leakage, since the CSV stores no domains) and reports metrics both as-is and deduplicated. See [docs/ml-methodology.md](../docs/ml-methodology.md#measured-performance-real-dataset-1200-rows-post-fix) for the numbers.

`evaluate_ml_adjustment.py` checks that the points the backend adds or subtracts for each model probability (`ml_service._adjustment_from_probability`) match the evidence that probability carries. It reports, per probability band, the share of legitimate and phishing URLs and the likelihood ratio, on out-of-fold CV and, with `--temporal`, on phishing newer than the training data. Re-run it after every retrain. See [Sizing the ML adjustment](../docs/ml-methodology.md#sizing-the-ml-adjustment).
