"""
Feedback ingestion pipeline.

Reads confirmed feedback entries from the SQLite store where the observed
label (what the model predicted) differs from the expected label (what the
user corrected it to). Exports them as CSV for manual review and future
dataset augmentation.

IMPORTANT — current store limitations:
  The feedback store records only the URL *hostname*, risk labels,
  note-presence flag, sanitized request ID, and timestamp.
  It does not store the full URL, DOM features, or the feature vector used
  during analysis. This means exported rows cannot be fed directly into
  train_model.py — they need to be matched with a full crawl or enriched
  manually before they become training examples.

Workflow for turning feedback into training data:
  1. Run this script to export disagreements:
       python ml/ingest_feedback.py --db feedback.db --out ml/datasets/feedback_review.csv
  2. For each row, re-crawl the recorded hostname or use a separately approved,
     privacy-reviewed dataset source. Do not add full URLs from backend logs to
     this repository.
  3. Re-extract features and add a row to ml/datasets/phishing_urls.csv.
  4. Re-train: python ml/train_model.py

See ml/datasets/README.md for the dataset column format and real-dataset
sources (PhishTank data dump, OpenPhish, ISCX-2016 URL dataset).
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path


EXPORT_COLUMNS = ["url_host", "observed_label", "expected_label", "notes_present", "request_id", "created_at"]


def export_disagreements(db_path: str, out_path: str, include_all: bool = False) -> int:
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if include_all:
        rows = conn.execute("SELECT * FROM feedback ORDER BY created_at").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM feedback WHERE observed != expected ORDER BY created_at"
        ).fetchall()

    conn.close()

    if not rows:
        print("No disagreement entries found.")
        return 0

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "url_host": row["url_host"],
                    "observed_label": row["observed"],
                    "expected_label": row["expected"],
                    "notes_present": row["note_present"],
                    "request_id": row["request_id"] or "",
                    "created_at": row["created_at"],
                }
            )

    print(f"Exported {len(rows)} rows to {out}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export feedback disagreements from SQLite store for dataset review."
    )
    parser.add_argument("--db", default="feedback.db", help="Path to feedback.db (default: feedback.db)")
    parser.add_argument(
        "--out",
        default="ml/datasets/feedback_review.csv",
        help="Output CSV path (default: ml/datasets/feedback_review.csv)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="include_all",
        help="Export all feedback entries, not just label disagreements",
    )
    args = parser.parse_args()
    sys.exit(export_disagreements(args.db, args.out, args.include_all))


if __name__ == "__main__":
    main()
