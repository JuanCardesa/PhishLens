# ML Methodology

## Objective

The model estimates whether a page has phishing-like risk signals from numeric URL and DOM features. It is an assistive signal in a hybrid scoring system, not a standalone verdict.

## Datasets

### Real dataset (preferred)

`ml/datasets/real_phishing_urls.csv` — built by `ml/datasets/build_dataset.py`.

| Source | Content | Size |
|--------|---------|------|
| [PhishTank public data dump](http://data.phishtank.com/data/online-valid.csv.gz) | Verified phishing URLs (`verified=yes`) | ~600 rows |
| [Tranco top-1M list](https://tranco-list.eu) | Legitimate domains (top 50 000 sampled) | ~600 rows |

To build the dataset (requires internet access, ~1–2 min):

```bash
cd ml
python datasets/build_dataset.py
python train_model.py
```

**Limitation:** DOM features (`has_password_field`, `num_forms`, etc.) are set to `0` for all
URL-only rows because they require a live browser session to collect. The model therefore relies
entirely on URL-derived signals when evaluated against this dataset. Real-world inference still
uses DOM features from the extension's content script.

### Synthetic demo dataset (fallback)

`ml/datasets/demo_phishing_urls.csv` is a small synthetic set used only to validate the
training pipeline when the real dataset has not been built yet. Do not treat metrics from
this dataset as production evidence.

`train_model.py` auto-detects which dataset is present and logs which one it used.

## Model Metrics

Run the full pipeline to generate metrics:

```bash
cd ml
python train_model.py   # prints CV accuracy, classification report, feature importances
python evaluate_model.py  # re-evaluates the saved artifact
```

Metrics to track: accuracy, precision, recall, F1-score, AUC-ROC, confusion matrix.
Prioritize recall for phishing URLs while keeping the false-positive rate on legitimate
pages (e.g. bank login pages) below 10 %.

## Features

Initial features mirror the backend and extension:

- URL length, dots, hyphens, IP domain, `@`, HTTPS, subdomain count.
- Suspicious keyword count, punycode, domain entropy.
- DOM password field, form count, external form action, iframe count, external link ratio, hidden inputs.

## Models

- Baseline: Logistic Regression.
- Initial primary model: RandomForestClassifier.

The training script stores both the primary model and baseline metadata in a joblib artifact.

## Metrics

Track accuracy, precision, recall, F1-score, and confusion matrix. In future datasets, prioritize recall for malicious URLs while controlling false positives for normal login and banking pages.

## Future Data Sources

Use legally available, documented datasets only. Candidate sources include public phishing URL feeds, benign URL corpora, internally generated safe examples, and browser telemetry only if collected with explicit consent and strict privacy controls.

## Limitations

Phishing behavior changes quickly. URL-only and DOM-only signals can be bypassed. The model needs regular retraining, drift checks, and careful review of false positives.
