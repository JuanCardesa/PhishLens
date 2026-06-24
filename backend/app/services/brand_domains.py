from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Fallback used only if the JSON config file is missing or unreadable, so a
# bad deployment path never disables typosquat/combosquat/brand-impersonation
# detection outright. Kept in sync with app/data/brand_domains.json and with
# extension/src/data/brand-domains.json (the extension's seed copy).
_SEED_BRAND_DOMAINS: tuple[str, ...] = (
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


def _resolve_brand_domains_path(configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path

    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate

    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / path


def load_brand_domains(path: Path | None = None) -> tuple[str, ...]:
    """Load the curated brand-domain list used by typosquat/combosquat/
    brand-impersonation detection from a JSON file, falling back to a small
    built-in seed list if the file is missing, unreadable, or malformed.

    Operators can point PHISHLENS_BRAND_DOMAINS_PATH at an updated list
    (e.g. a larger brand-coverage file) without a code change or redeploy.
    """
    resolved = path if path is not None else _resolve_brand_domains_path(get_settings().brand_domains_path)

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Falling back to built-in seed brand domain list (path=%s, reason=%s)", resolved, exc)
        return _SEED_BRAND_DOMAINS

    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) and item for item in raw):
        logger.warning("Brand domains file has an invalid shape, falling back to seed list (path=%s)", resolved)
        return _SEED_BRAND_DOMAINS

    return tuple(raw)


KNOWN_BRAND_DOMAINS: tuple[str, ...] = load_brand_domains()
