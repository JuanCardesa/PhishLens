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
python ml/evaluate_model.py
```

`evaluate_model.py` validates the saved artifact's dataset name and SHA-256 before reporting metrics, so stale local models fail fast instead of being evaluated against the wrong CSV.
