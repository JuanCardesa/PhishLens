# PhishLens ML

This folder contains the first machine learning pipeline for PhishLens.

The dataset included in `datasets/demo_phishing_urls.csv` is synthetic and only exists to validate the training and inference flow. It is not representative enough for production decisions.

## Train

```bash
python ml/train_model.py
```

The script trains a Logistic Regression baseline and a RandomForestClassifier, then writes the selected model to `ml/models/phishlens_model.joblib`.

## Evaluate

```bash
python ml/evaluate_model.py
```

Replace the demo CSV with a curated, legally usable dataset before treating model metrics as meaningful.
