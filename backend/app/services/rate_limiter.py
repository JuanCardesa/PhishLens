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
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[str, deque[float]] = {}

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
            return RateLimitDecision(allowed=True)

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


RATE_LIMITER = InMemoryRateLimiter()


def rate_limit_dependency(route_name: str):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.enable_rate_limiting:
            return

        client_host = request.client.host if request.client else "unknown"
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
