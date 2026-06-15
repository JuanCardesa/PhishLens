from app.services.cache import TTLCache


def test_ttl_cache_prunes_expired_entries_on_set(monkeypatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: now)
    cache = TTLCache[str](ttl_seconds=1)

    cache.set("old", "value")

    now = 102.0
    cache.set("new", "value")

    assert cache.get("old") is None
    assert cache.get("new") == "value"
