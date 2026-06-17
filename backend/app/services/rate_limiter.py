from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from math import ceil
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.services.diagnostics import DIAGNOSTICS


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    def __init__(self, cleanup_interval: int = 300) -> None:
        self._lock = Lock()
        self._requests: dict[str, deque[float]] = {}
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.monotonic()

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            requests = self._requests.setdefault(key, deque())
            while requests and requests[0] <= window_start:
                requests.popleft()

            if len(requests) >= limit:
                retry_after = max(1, ceil(window_seconds - (now - requests[0])))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            requests.append(now)
            self._maybe_prune_empty_keys(now)
            return RateLimitDecision(allowed=True)

    def _maybe_prune_empty_keys(self, now: float) -> None:
        """Remove keys whose deques are empty, executed at most once per cleanup_interval."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        empty_keys = [k for k, v in self._requests.items() if not v]
        for k in empty_keys:
            del self._requests[k]

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


RATE_LIMITER = InMemoryRateLimiter()


def _resolve_client_ip(request: Request, behind_proxy: bool) -> str:
    """Return the real client IP.

    When behind_proxy is True, reads the leftmost address from X-Forwarded-For,
    which standard reverse proxies (nginx, Caddy, AWS ALB) populate with the
    original client IP. Only enable PHISHLENS_BEHIND_PROXY when the backend is
    not directly internet-facing; blindly trusting this header on a public
    endpoint lets callers spoof their IP and bypass rate limiting.
    """
    if behind_proxy:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(route_name: str):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.enable_rate_limiting:
            return

        client_host = _resolve_client_ip(request, settings.behind_proxy)
        limit = (
            settings.analyze_rate_limit_per_minute
            if route_name == "analyze"
            else settings.report_rate_limit_per_minute
        )
        decision = RATE_LIMITER.check(
            key=f"{route_name}:{client_host}",
            limit=limit,
            window_seconds=settings.rate_limit_window_seconds,
        )

        if not decision.allowed:
            DIAGNOSTICS.record_rate_limit(route_name)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )

    return dependency


def clear_rate_limiter() -> None:
    RATE_LIMITER.clear()
