from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, max_size: int = 1000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._items: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        item = self._items.get(key)
        if item is None:
            return None

        if item.expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None

        return item.value

    def set(self, key: str, value: T) -> None:
        now = time.monotonic()
        self._prune_expired(now)
        # After pruning, evict the soonest-to-expire entry if still at capacity.
        if key not in self._items and len(self._items) >= self.max_size:
            oldest = min(self._items, key=lambda k: self._items[k].expires_at)
            del self._items[oldest]
        self._items[key] = CacheEntry(value=value, expires_at=now + self.ttl_seconds)

    def clear(self) -> None:
        self._items.clear()

    def _prune_expired(self, now: float) -> None:
        expired_keys = [key for key, item in self._items.items() if item.expires_at <= now]
        for key in expired_keys:
            self._items.pop(key, None)
