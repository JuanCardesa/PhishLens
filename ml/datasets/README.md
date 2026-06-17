# ML Datasets

## Current dataset

`demo_phishing_urls.csv` — 12 synthetic rows used exclusively to validate the
ML pipeline end-to-end. **Not suitable for production use.** Performance metrics
from this dataset are meaningless — it is too small and not drawn from real traffic.

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
1. Retrieve the original full URL (from server logs or re-crawl the hostname).
2. Re-extract all 16 features using the same feature extractor.
3. Set `label` to `1` if the user flagged it as phishing, `0` if safe.
4. Append the completed row to this directory as a new CSV and re-run `train_model.py`.
