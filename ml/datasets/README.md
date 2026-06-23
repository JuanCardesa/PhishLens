# ML Datasets

## Current datasets

`real_phishing_urls.csv` — 1200 rows built by `build_dataset.py` from the PhishTank
verified-phishing dump (600 rows) and the Tranco top-1M list (600 rows). Contains only the
16 numeric features and a label, never raw URLs or domains. `train_model.py` and
`evaluate_model.py` prefer this file automatically when it is present. See
[docs/ml-methodology.md](../../docs/ml-methodology.md) for measured accuracy. Re-run
`python datasets/build_dataset.py` to refresh it from a current PhishTank/Tranco snapshot.

`demo_phishing_urls.csv` — 12 synthetic rows used exclusively to validate the
ML pipeline end-to-end before the real dataset existed, and as an offline fallback if
`build_dataset.py` cannot reach the network. **Not suitable for production use.** Performance
metrics from this dataset are meaningless — it is too small and not drawn from real traffic.

## CSV column format

All training CSVs must contain these 17 columns (16 features + label):

| Column | Type | Description |
|--------|------|-------------|
| `url_length` | int | Total character length of the URL |
| `num_dots` | int | Number of `.` characters in the URL |
| `num_hyphens` | int | Number of `-` characters in the URL |
| `uses_ip_domain` | 0/1 | Domain is a raw IP address |
| `has_at_symbol` | 0/1 | URL contains `@` |
| `uses_https` | 0/1 | Scheme is `https` |
| `num_subdomains` | int | Number of subdomain labels |
| `suspicious_keyword_count` | int | Count of known phishing keywords in the URL |
| `uses_punycode` | 0/1 | Domain contains an `xn--` ACE label |
| `domain_entropy` | float | Shannon entropy of the registered domain string |
| `has_password_field` | 0/1 | Page DOM contains a password input |
| `num_forms` | int | Number of `<form>` elements on the page |
| `external_form_action` | 0/1 | Any form posts to a different origin |
| `num_iframes` | int | Number of `<iframe>` elements |
| `external_links_ratio` | float | Fraction of links pointing to external domains |
| `has_hidden_inputs` | 0/1 | Page contains `<input type="hidden">` |
| `label` | 0/1 | Ground truth — 1 = phishing, 0 = legitimate |

## Real dataset sources

These publicly available datasets can be used to build a production-grade
training set. Download, extract, and reformat to match the column schema above.

### PhishTank data dump
- URL: https://www.phishtank.com/developer_info.php
- Format: CSV / XML with verified phishing URLs
- Provides phishing-positive examples. Pair with a legitimate URL crawl for negatives.

### OpenPhish
- URL: https://openphish.com/
- Format: plain text URL list (feed)
- Actively updated list of phishing URLs. Use for phishing-positive examples.

### ISCX-2016 URL dataset
- Citation: Mamun et al., "Detecting Malicious URLs Using Lexical Analysis" (2016)
- Contains ~36 000 URLs labeled across four classes (benign, phishing, malware, defacement).
- Available via the University of New Brunswick (UNB) ISCX dataset repository.
- Map `phishing` → 1, `benign` → 0; discard `malware` and `defacement` rows or treat them as negative.

### Alexa / Tranco Top-1M
- URL: https://tranco-list.eu/
- Provides legitimate domain examples (negatives). Crawl the top-N domains and
  extract DOM features, then label as 0.

## Adding feedback-derived examples

After running `python ml/ingest_feedback.py`, review `feedback_review.csv`.
For each row:
1. Re-crawl the recorded hostname or use a separately approved, privacy-reviewed dataset source.
2. Re-extract all 16 features using the same feature extractor. Do not add full URLs from backend logs to this repository.
3. Set `label` to `1` if the user flagged it as phishing, `0` if safe.
4. Append the completed row to this directory as a new CSV and re-run `train_model.py`.
