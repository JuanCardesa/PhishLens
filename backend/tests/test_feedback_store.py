from pathlib import Path

import pytest

from app.services.feedback_store import FeedbackEntry, SQLiteFeedbackStore, _DisabledFeedbackStore, _make_store


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_feedback.db")


def _entry(**overrides) -> FeedbackEntry:
    defaults = dict(
        url_host="example.com",
        observed_label="safe",
        expected_label="dangerous",
        notes_present=False,
        request_id="req-abc",
        created_at="2026-06-17T00:00:00+00:00",
    )
    return FeedbackEntry(**{**defaults, **overrides})


def test_sqlite_store_records_and_counts(tmp_db: str) -> None:
    store = SQLiteFeedbackStore(tmp_db)
    assert store.count() == 0
    store.record(_entry())
    assert store.count() == 1
    store.record(_entry(url_host="other.com", notes_present=True))
    assert store.count() == 2


def test_sqlite_store_persists_across_instances(tmp_db: str) -> None:
    SQLiteFeedbackStore(tmp_db).record(_entry())
    assert SQLiteFeedbackStore(tmp_db).count() == 1


def test_sqlite_store_is_thread_safe(tmp_db: str) -> None:
    import threading

    store = SQLiteFeedbackStore(tmp_db)
    errors: list[Exception] = []

    def worker() -> None:
        try:
            for _ in range(10):
                store.record(_entry())
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert store.count() == 50


def test_disabled_store_is_noop() -> None:
    store = _DisabledFeedbackStore()
    store.record(_entry())
    assert store.count() == 0


def test_make_store_returns_disabled_when_path_empty() -> None:
    assert isinstance(_make_store(""), _DisabledFeedbackStore)
    assert isinstance(_make_store("   "), _DisabledFeedbackStore)


def test_make_store_creates_parent_dirs(tmp_path: Path) -> None:
    db_path = str(tmp_path / "nested" / "dir" / "feedback.db")
    store = _make_store(db_path)
    assert isinstance(store, SQLiteFeedbackStore)
    store.record(_entry())
    assert store.count() == 1
