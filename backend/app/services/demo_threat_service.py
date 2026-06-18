from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.services.url_normalizer import normalize_url


DEMO_THREAT_MARKER = "phishlens-demo-dangerous"
# Only "localhost" is reachable here — private IP literals (127.0.0.1, ::1) are
# rejected by normalize_url before this service is called.
DEMO_HOSTS = {"localhost"}


@dataclass(frozen=True)
class DemoThreatResult:
    checked: bool
    matched: bool = False


def check_demo_threat_source(url: str, settings: Settings | None = None) -> DemoThreatResult:
    settings = settings or get_settings()
    if not settings.enable_demo_threat_source:
        return DemoThreatResult(checked=False)

    parsed = urlparse(normalize_url(url))
    hostname = (parsed.hostname or "").lower()
    path_and_query = f"{parsed.path}?{parsed.query}".lower()
    return DemoThreatResult(
        checked=True,
        matched=hostname in DEMO_HOSTS and DEMO_THREAT_MARKER in path_and_query,
    )
