# ML Methodology

## Objective

The model estimates whether a page has phishing-like risk signals from numeric URL and DOM features. It is an assistive signal in a hybrid scoring system, not a standalone verdict.

## Current Dataset

`ml/datasets/demo_phishing_urls.csv` is synthetic demo data used only to validate the pipeline.

Do not treat demo metrics as production evidence.

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
