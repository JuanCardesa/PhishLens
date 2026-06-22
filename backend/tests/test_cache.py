import pytest

from app.services.cache import TTLCache


def test_ttl_cache_prunes_expired_entries_on_set(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: now)
    cache = TTLCache[str](ttl_seconds=1)

    cache.set("old", "value")

    now = 102.0
    cache.set("new", "value")

    assert cache.get("old") is None
    assert cache.get("new") == "value"


def test_ttl_cache_evicts_oldest_entry_when_max_size_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: now)
    cache = TTLCache[str](ttl_seconds=60, max_size=2)

    cache.set("a", "first")
    now = 101.0
    cache.set("b", "second")
    now = 102.0
    # "a" expires soonest; adding "c" should evict it
    cache.set("c", "third")

    assert cache.get("a") is None
    assert cache.get("b") == "second"
    assert cache.get("c") == "third"


def test_ttl_cache_updating_existing_key_does_not_evict(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: now)
    cache = TTLCache[str](ttl_seconds=60, max_size=2)

    cache.set("a", "first")
    cache.set("b", "second")
    # Updating an existing key must not trigger eviction
    cache.set("a", "updated")

    assert cache.get("a") == "updated"
    assert cache.get("b") == "second"
