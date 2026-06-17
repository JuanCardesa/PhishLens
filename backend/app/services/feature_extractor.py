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

    return URLFeatures(
        url_length=len(url),
        num_dots=url.count("."),
        num_hyphens=url.count("-"),
        uses_ip_domain=uses_ip_domain,
        has_at_symbol="@" in url,
        uses_https=parsed.scheme == "https",
        num_subdomains=0 if uses_ip_domain else max(0, len(labels) - 2),
        suspicious_keywords=keyword_matches,
        uses_punycode="xn--" in hostname,
        domain_entropy=round(_shannon_entropy(registered_domain.replace(".", "")), 3),
        domain=hostname,
    )


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
