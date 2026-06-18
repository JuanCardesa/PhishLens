"""Build a real phishing/legitimate URL dataset for PhishLens.

Downloads:
  - PhishTank verified phishing URLs (public data dump, no API key needed)
  - Tranco top-1M list for legitimate URL samples

Extracts URL-only features (the 10 non-DOM columns) and sets DOM features to 0
for all entries, since DOM data requires a live browser session. This limitation
is documented in docs/ml-methodology.md.

Output: ml/datasets/real_phishing_urls.csv  (~1 000–1 200 rows, balanced)

Usage:
    cd ml
    python datasets/build_dataset.py

Requirements (already in backend/requirements.txt or standard library):
    pandas, requests (or urllib), math, re, unicodedata, ipaddress
"""

from __future__ import annotations

import csv
import gzip
import io
import ipaddress
import logging
import math
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "datasets" / "real_phishing_urls.csv"

PHISHTANK_DUMP_URL = "http://data.phishtank.com/data/online-valid.csv.gz"
TRANCO_LIST_URL = "https://tranco-list.eu/download/latest/full"

PHISHING_SAMPLE = 600
LEGIT_SAMPLE = 600
TRANCO_TOP_K = 50_000

SUSPICIOUS_KEYWORDS = [
    "login", "signin", "verify", "secure", "account",
    "update", "confirm", "banking", "paypal", "password",
]

FEATURE_COLUMNS = [
    "url_length", "num_dots", "num_hyphens", "uses_ip_domain", "has_at_symbol",
    "uses_https", "num_subdomains", "suspicious_keyword_count", "uses_punycode",
    "domain_entropy",
    # DOM features — always 0 for downloaded URLs (require live browser).
    "has_password_field", "num_forms", "external_form_action",
    "num_iframes", "external_links_ratio", "has_hidden_inputs",
    "label",
]


class Row(TypedDict):
    url_length: int
    num_dots: int
    num_hyphens: int
    uses_ip_domain: int
    has_at_symbol: int
    uses_https: int
    num_subdomains: int
    suspicious_keyword_count: int
    uses_punycode: int
    domain_entropy: float
    has_password_field: int
    num_forms: int
    external_form_action: int
    num_iframes: int
    external_links_ratio: float
    has_hidden_inputs: int
    label: int


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) / len(s) for c in set(s)}
    return -sum(p * math.log2(p) for p in freq.values())


def _uses_ip_domain(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def _is_punycode(hostname: str) -> bool:
    return "xn--" in hostname.lower()


def _count_subdomains(hostname: str) -> int:
    parts = hostname.rstrip(".").split(".")
    return max(0, len(parts) - 2)


def extract_url_features(url: str, label: int) -> Row | None:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        path = parsed.path or ""
        uses_https = int(parsed.scheme == "https")
        host_and_path = hostname + path
        keyword_count = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in host_and_path.lower())
        punycode = int(_is_punycode(hostname))

        return {
            "url_length": len(url),
            "num_dots": hostname.count("."),
            "num_hyphens": hostname.count("-"),
            "uses_ip_domain": int(_uses_ip_domain(hostname)),
            "has_at_symbol": int("@" in url),
            "uses_https": uses_https,
            "num_subdomains": _count_subdomains(hostname),
            "suspicious_keyword_count": keyword_count,
            "uses_punycode": punycode,
            "domain_entropy": round(_shannon_entropy(hostname), 4),
            # DOM features not available without browser — set to 0.
            "has_password_field": 0,
            "num_forms": 0,
            "external_form_action": 0,
            "num_iframes": 0,
            "external_links_ratio": 0.0,
            "has_hidden_inputs": 0,
            "label": label,
        }
    except Exception:
        return None


def fetch_phishtank_urls(n: int) -> list[str]:
    logger.info("Downloading PhishTank data dump…")
    try:
        with urllib.request.urlopen(PHISHTANK_DUMP_URL, timeout=60) as resp:
            raw = resp.read()
        with gzip.open(io.BytesIO(raw)) as gz:
            text = gz.read().decode("utf-8", errors="replace")
    except Exception as exc:
        logger.error("Failed to download PhishTank dump: %s", exc)
        return []

    urls: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row.get("verified", "").lower() == "yes":
            url = row.get("url", "").strip()
            if url.startswith(("http://", "https://")):
                urls.append(url)
        if len(urls) >= n * 3:
            break

    logger.info("PhishTank: %d verified phishing URLs collected", len(urls))
    return urls[:n]


def fetch_tranco_urls(n: int, top_k: int) -> list[str]:
    logger.info("Downloading Tranco top-%d list…", top_k)
    try:
        with urllib.request.urlopen(TRANCO_LIST_URL, timeout=60) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        logger.error("Failed to download Tranco list: %s", exc)
        return []

    domains: list[str] = []
    for line in text.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) == 2:
            rank_str, domain = parts
            try:
                rank = int(rank_str)
            except ValueError:
                continue
            if rank > top_k:
                break
            domain = domain.strip().lower()
            if domain and "." in domain:
                domains.append(f"https://{domain}/")
        if len(domains) >= n * 2:
            break

    logger.info("Tranco: %d legitimate domains sampled", len(domains))
    import random
    random.seed(42)
    random.shuffle(domains)
    return domains[:n]


def main() -> int:
    phishing_urls = fetch_phishtank_urls(PHISHING_SAMPLE)
    legit_urls = fetch_tranco_urls(LEGIT_SAMPLE, TRANCO_TOP_K)

    if not phishing_urls or not legit_urls:
        logger.error("Dataset build failed — check network connectivity and try again.")
        return 1

    rows: list[Row] = []
    for url in phishing_urls:
        row = extract_url_features(url, label=1)
        if row:
            rows.append(row)

    for url in legit_urls:
        row = extract_url_features(url, label=0)
        if row:
            rows.append(row)

    import random
    random.seed(42)
    random.shuffle(rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    n_phishing = sum(1 for r in rows if r["label"] == 1)
    n_legit = sum(1 for r in rows if r["label"] == 0)
    logger.info(
        "Dataset saved → %s  (%d rows: %d phishing, %d legitimate)",
        OUT_PATH,
        len(rows),
        n_phishing,
        n_legit,
    )
    logger.info(
        "Note: DOM features (has_password_field, num_forms, etc.) are 0 for all rows "
        "because they require a live browser session. See docs/ml-methodology.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
