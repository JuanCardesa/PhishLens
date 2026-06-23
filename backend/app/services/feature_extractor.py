from __future__ import annotations

import ipaddress
import math
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlparse


SUSPICIOUS_KEYWORDS = (
    "login",
    "verify",
    "account",
    "secure",
    "update",
    "password",
    "bank",
    "wallet",
)

# Curated list of frequently-impersonated brand domains. Used as the
# reference set for typosquatting (Levenshtein) and combosquatting
# (brand name embedded in a longer label) detection.
KNOWN_BRAND_DOMAINS = (
    "google.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "whatsapp.com",
    "amazon.com",
    "apple.com",
    "icloud.com",
    "microsoft.com",
    "outlook.com",
    "office.com",
    "netflix.com",
    "paypal.com",
    "ebay.com",
    "linkedin.com",
    "twitter.com",
    "github.com",
    "dropbox.com",
    "yahoo.com",
    "bankofamerica.com",
    "chase.com",
    "wellsfargo.com",
    "americanexpress.com",
    "coinbase.com",
    "binance.com",
    "adobe.com",
)

# Brand names shorter than this produce too many coincidental matches
# (e.g. "x.com") to be a useful typosquatting signal.
MIN_BRAND_NAME_LENGTH = 4

# Maximum Levenshtein distance still considered a plausible typosquat.
MAX_TYPOSQUAT_DISTANCE = 2


@dataclass(frozen=True)
class URLFeatures:
    url_length: int
    num_dots: int
    num_hyphens: int
    uses_ip_domain: bool
    has_at_symbol: bool
    uses_https: bool
    num_subdomains: int
    suspicious_keywords: tuple[str, ...]
    uses_punycode: bool
    domain_entropy: float
    domain: str
    typosquat_target: str | None
    typosquat_distance: int | None


def extract_url_features(url: str) -> URLFeatures:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    labels = [label for label in hostname.split(".") if label]
    uses_ip_domain = _is_ip_address(hostname)
    registered_domain_parts = labels[-2:] if len(labels) >= 2 else labels
    registered_domain = ".".join(registered_domain_parts)
    # Limit keyword scan to hostname + path only; query strings like
    # ?q=bank+verify are common on legitimate search engines and cause
    # false positives when the full URL is checked.
    hostname_and_path = (hostname + (parsed.path or "")).lower()
    keyword_matches = tuple(keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in hostname_and_path)
    typosquat_target, typosquat_distance = (
        (None, None) if uses_ip_domain else _detect_typosquatting(registered_domain)
    )

    return URLFeatures(
        url_length=len(url),
        num_dots=hostname_and_path.count("."),  # query string excluded to avoid false positives
        num_hyphens=url.count("-"),
        uses_ip_domain=uses_ip_domain,
        has_at_symbol="@" in url,
        uses_https=parsed.scheme == "https",
        num_subdomains=0 if uses_ip_domain else max(0, len(labels) - 2),
        suspicious_keywords=keyword_matches,
        uses_punycode="xn--" in hostname,
        domain_entropy=round(_shannon_entropy(registered_domain.replace(".", "")), 3),
        domain=hostname,
        typosquat_target=typosquat_target,
        typosquat_distance=typosquat_distance,
    )


def _detect_typosquatting(registered_domain: str) -> tuple[str | None, int | None]:
    """Compare the registered domain against known brand domains.

    Catches two patterns: classic typosquatting (a small Levenshtein edit
    distance, e.g. "paypa1.com") and combosquatting (the brand name embedded
    in a longer label, e.g. "paypal-secure.com"). Returns the closest brand
    domain and the distance used to flag it, or (None, None) if no plausible
    match is found.
    """
    if not registered_domain or registered_domain in KNOWN_BRAND_DOMAINS:
        return None, None

    domain_label = registered_domain.split(".")[0]
    best_target: str | None = None
    best_distance: int | None = None

    for brand_domain in KNOWN_BRAND_DOMAINS:
        brand_label = brand_domain.split(".")[0]
        if len(brand_label) < MIN_BRAND_NAME_LENGTH:
            continue

        if brand_label != domain_label and brand_label in domain_label:
            distance = 1  # combosquatting: brand name embedded with extra characters
        else:
            distance = _levenshtein_distance(registered_domain, brand_domain)

        if distance <= MAX_TYPOSQUAT_DISTANCE and (best_distance is None or distance < best_distance):
            best_distance = distance
            best_target = brand_domain

    return best_target, best_distance


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current_row[j] = min(
                previous_row[j] + 1,  # deletion
                current_row[j - 1] + 1,  # insertion
                previous_row[j - 1] + cost,  # substitution
            )
        previous_row = current_row

    return previous_row[-1]


def _is_ip_address(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0

    length = len(value)
    counts = Counter(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())
