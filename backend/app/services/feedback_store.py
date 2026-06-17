from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class FeedbackEntry:
    url_host: str
    observed_label: str
    expected_label: str
    notes_present: bool
    request_id: str | None
    created_at: str


class SQLiteFeedbackStore:
    """Thread-safe SQLite store for user feedback.

    Stores only non-sensitive metadata: hostname (not full URL), labels, and
    whether a note was present. Full URLs, page content, and notes text are
    never persisted — consistent with docs/privacy.md.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_host    TEXT    NOT NULL,
                    observed    TEXT    NOT NULL,
                    expected    TEXT    NOT NULL,
                    note_present INTEGER NOT NULL DEFAULT 0,
                    request_id  TEXT,
                    created_at  TEXT    NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")

    def record(self, entry: FeedbackEntry) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback
                    (url_host, observed, expected, note_present, request_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.url_host,
                    entry.observed_label,
                    entry.expected_label,
                    1 if entry.notes_present else 0,
                    entry.request_id,
                    entry.created_at,
                ),
            )

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()
            return row[0] if row else 0


class _DisabledFeedbackStore:
    """No-op store used when PHISHLENS_FEEDBACK_DB_PATH is empty."""

    def record(self, entry: FeedbackEntry) -> None:
        pass

    def count(self) -> int:
        return 0


def _make_store(db_path: str) -> SQLiteFeedbackStore | _DisabledFeedbackStore:
    if not db_path.strip():
        return _DisabledFeedbackStore()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return SQLiteFeedbackStore(db_path)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# Module-level singleton; initialised once on first import.
def _init_feedback_store() -> SQLiteFeedbackStore | _DisabledFeedbackStore:
    from app.core.config import get_settings  # local import avoids circular deps
    return _make_store(get_settings().feedback_db_path)


FEEDBACK_STORE: SQLiteFeedbackStore | _DisabledFeedbackStore = _init_feedback_store()
