from __future__ import annotations

import ipaddress
import math
import unicodedata
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlparse

from app.services.brand_domains import KNOWN_BRAND_DOMAINS

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

# Brand names shorter than this produce too many coincidental matches
# (e.g. "x.com") to be a useful typosquatting signal.
MIN_BRAND_NAME_LENGTH = 4

# Maximum Levenshtein distance still considered a plausible typosquat.
MAX_TYPOSQUAT_DISTANCE = 2

# Common two-label public suffixes. This is intentionally conservative rather
# than a full PSL implementation so the extension and backend can stay in sync
# without adding bundle/runtime dependencies.
COMMON_SECOND_LEVEL_PUBLIC_SUFFIX_LABELS = frozenset({"ac", "co", "com", "edu", "gov", "net", "org"})

# Non-exhaustive table of Cyrillic/Greek characters commonly used in
# homograph (IDN spoofing) attacks, mapped to the Latin letter they visually
# resemble. Covers the lookalikes seen in real-world phishing reports (e.g.
# the "apple.com" -> "аррӏе.com" spoof); not a full Unicode confusables table.
CONFUSABLE_MAP = {
    # Cyrillic
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "х": "x",
    "у": "y",
    "ѕ": "s",
    "і": "i",
    "ј": "j",
    "ӏ": "l",
    # Greek
    "α": "a",
    "ο": "o",
    "ρ": "p",
    "υ": "y",
    "ι": "i",
    "χ": "x",
}

# Unicode character category name prefixes used to bucket characters into
# scripts for mixed-script detection. Digits, hyphens, and unrecognized
# characters are treated as script-neutral to avoid false positives.
_SCRIPT_NAME_PREFIXES = (
    "LATIN",
    "CYRILLIC",
    "GREEK",
    "ARMENIAN",
    "HEBREW",
    "ARABIC",
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "HANGUL",
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
    typosquat_target: str | None
    typosquat_distance: int | None
    typosquat_is_homograph: bool
    mixed_script_label: bool
    brand_subdomain_target: str | None


def extract_url_features(url: str) -> URLFeatures:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    labels = [label for label in hostname.split(".") if label]
    uses_ip_domain = _is_ip_address(hostname)
    registered_domain = registrable_domain_from_hostname(hostname)
    registered_domain_parts = registered_domain.split(".") if registered_domain else []
    decoded_labels = tuple(_idna_decode_label(label).lower() for label in labels)
    decoded_hostname = ".".join(decoded_labels)
    decoded_registered_domain_parts = (
        decoded_labels[-len(registered_domain_parts) :] if registered_domain_parts else ()
    )
    decoded_registered_domain = ".".join(decoded_registered_domain_parts)
    registered_domain_label = decoded_registered_domain_parts[0] if decoded_registered_domain_parts else ""
    # Limit keyword scan to hostname + path only; query strings like
    # ?q=bank+verify are common on legitimate search engines and cause
    # false positives when the full URL is checked.
    hostname_and_path = (hostname + (parsed.path or "")).lower()
    decoded_hostname_and_path = (decoded_hostname + (parsed.path or "")).lower()
    keyword_matches = tuple(keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in hostname_and_path)

    is_non_ascii_label = any(ord(char) > 127 for char in registered_domain_label)
    normalized_label = _normalize_confusables(registered_domain_label)
    mixed_script_label = False if uses_ip_domain else _has_mixed_script(registered_domain_label)

    typosquat_target, typosquat_distance, typosquat_is_homograph = (
        (None, None, False)
        if uses_ip_domain
        else _detect_typosquatting(registered_domain, normalized_label, is_non_ascii_label)
    )

    subdomain_label_count = 0 if uses_ip_domain else max(0, len(labels) - len(registered_domain_parts))
    subdomain_labels = list(decoded_labels[:subdomain_label_count]) if subdomain_label_count else []
    brand_subdomain_target = _detect_brand_subdomain_impersonation(registered_domain, subdomain_labels)
    # A leading "www" is a naming convention, not structure an attacker chose, so
    # it counts as neither a subdomain nor a dot. Counting it made www.paypal.com
    # look like phishing to the ML model (+20) while paypal.com got -10. Mirrored
    # in extension/src/utils/url-features.ts.
    www_prefix = 1 if subdomain_label_count > 0 and labels[0] == "www" else 0

    return URLFeatures(
        url_length=len(url),
        # query string excluded to avoid false positives
        num_dots=hostname_and_path.count(".") - www_prefix,
        num_hyphens=decoded_hostname_and_path.count("-"),
        uses_ip_domain=uses_ip_domain,
        has_at_symbol="@" in url,
        uses_https=parsed.scheme == "https",
        num_subdomains=subdomain_label_count - www_prefix,
        suspicious_keywords=keyword_matches,
        uses_punycode="xn--" in hostname,
        domain_entropy=round(_shannon_entropy(decoded_registered_domain.replace(".", "")), 3),
        domain=hostname,
        typosquat_target=typosquat_target,
        typosquat_distance=typosquat_distance,
        typosquat_is_homograph=typosquat_is_homograph,
        mixed_script_label=mixed_script_label,
        brand_subdomain_target=brand_subdomain_target,
    )


def _detect_brand_subdomain_impersonation(
    registered_domain: str, subdomain_labels: list[str]
) -> str | None:
    """Flag a known brand's full registered domain hidden in the subdomains.

    Attackers put the real brand domain in the left-hand labels so a glancing
    reader sees it first, e.g. ``paypal.com.account-verify.example`` — where the
    actual registrable domain is ``account-verify.example`` and typosquat/
    keyword checks (which only look at the registrable domain) see nothing.

    Requires the brand's *entire* registrable domain to appear as a consecutive
    run of subdomain labels (``paypal.com``, not the bare label ``paypal``),
    which keeps false positives low: a legitimate subdomain named after a brand
    (``visa.mycorp.example``) does not match, but the common look-alike pattern
    does. Skipped when the page's own registrable domain is itself a known brand
    (a legitimate ``login.paypal.com``). Returns the matched brand domain or
    ``None``.
    """
    if not registered_domain or registered_domain in KNOWN_BRAND_DOMAINS or not subdomain_labels:
        return None

    haystack = f".{'.'.join(subdomain_labels)}."
    for brand_domain in KNOWN_BRAND_DOMAINS:
        if f".{brand_domain}." in haystack:
            return brand_domain
    return None


def _idna_decode_label(label: str) -> str:
    """Decode a single punycode label (e.g. "xn--80ak6aa92e") to Unicode.

    Returns the label unchanged if it is not punycode-encoded or fails to
    decode (malformed punycode).
    """
    if not label.startswith("xn--"):
        return label

    try:
        return label.encode("ascii").decode("idna")
    except (UnicodeError, UnicodeDecodeError):
        return label


def _normalize_confusables(text: str) -> str:
    return "".join(CONFUSABLE_MAP.get(char, char) for char in text)


def _char_script(char: str) -> str | None:
    if char.isdigit() or char in ("-", "_"):
        return None

    try:
        name = unicodedata.name(char)
    except ValueError:
        return None

    for prefix in _SCRIPT_NAME_PREFIXES:
        if name.startswith(prefix):
            return prefix

    return None


def _has_mixed_script(label: str) -> bool:
    scripts = {script for char in label if (script := _char_script(char)) is not None}
    return len(scripts) > 1


def _registrable_domain_parts(labels: list[str]) -> list[str]:
    if len(labels) < 2:
        return labels

    if (
        len(labels) >= 3
        and len(labels[-1]) == 2
        and labels[-2] in COMMON_SECOND_LEVEL_PUBLIC_SUFFIX_LABELS
    ):
        return labels[-3:]

    return labels[-2:]


def registrable_domain_from_hostname(hostname: str) -> str:
    labels = [label for label in hostname.lower().rstrip(".").split(".") if label]
    return ".".join(_registrable_domain_parts(labels))


def _detect_typosquatting(
    registered_domain: str, domain_label: str, is_non_ascii_label: bool
) -> tuple[str | None, int | None, bool]:
    """Compare the registered domain against known brand domains.

    `domain_label` is already IDNA-decoded and confusable-normalized, so this
    catches three patterns with a single comparison: classic typosquatting (a
    small Levenshtein edit distance, e.g. "paypa1.net"), combosquatting (the
    brand name as a hyphen-delimited token in a longer label, e.g.
    "paypal-secure.com"), and homograph attacks (look-alike Unicode characters
    that normalize to the brand name, e.g. the punycode form of "аррӏе.com").

    An exact normalized match (distance 0) is only flagged when the label is
    non-ASCII/homograph; an ASCII label that exactly matches a brand name on a
    different suffix (e.g. "google.co.uk") is a plausible legitimate regional
    domain and is not flagged.

    Returns (target_domain, distance, is_homograph), or (None, None, False) if
    no plausible match is found.
    """
    if (
        not registered_domain
        or registered_domain in KNOWN_BRAND_DOMAINS
        or not domain_label
        or len(domain_label) < MIN_BRAND_NAME_LENGTH
    ):
        return None, None, False

    best_target: str | None = None
    best_distance: int | None = None

    for brand_domain in KNOWN_BRAND_DOMAINS:
        brand_label = brand_domain.split(".")[0]
        if len(brand_label) < MIN_BRAND_NAME_LENGTH:
            continue

        if _is_hyphen_delimited_combo(domain_label, brand_label):
            distance = 1
        else:
            distance = _levenshtein_distance(domain_label, brand_label)
            if distance == 0 and not is_non_ascii_label:
                continue

        if distance <= MAX_TYPOSQUAT_DISTANCE and (best_distance is None or distance < best_distance):
            best_distance = distance
            best_target = brand_domain

    if best_target is None:
        return None, None, False

    return best_target, best_distance, is_non_ascii_label


def _is_hyphen_delimited_combo(domain_label: str, brand_label: str) -> bool:
    if domain_label == brand_label or "-" not in domain_label:
        return False

    return brand_label in (token for token in domain_label.split("-") if token)


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
