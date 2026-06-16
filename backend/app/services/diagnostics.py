from __future__ import annotations

from collections import Counter
from threading import Lock
from typing import Mapping

from app.schemas.analysis import AnalysisSources, RiskLabel


class DiagnosticsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()
        self._labels: Counter[str] = Counter()
        self._sources: Counter[str] = Counter()

    def increment(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[key] += amount

    def record_analysis(self, label: RiskLabel, sources: AnalysisSources) -> None:
        with self._lock:
            self._counters["analysis_requests"] += 1
            self._labels[label] += 1
            for source, enabled in sources.model_dump().items():
                if enabled:
                    self._sources[source] += 1

    def record_report(self) -> None:
        self.increment("feedback_reports")

    def record_rate_limit(self, route_name: str) -> None:
        with self._lock:
            self._counters["rate_limited_requests"] += 1
            self._counters[f"{route_name}_rate_limited"] += 1

    def record_cache(self, service_name: str, hit: bool) -> None:
        suffix = "hits" if hit else "misses"
        self.increment(f"{service_name}_cache_{suffix}")

    def record_external_error(self, service_name: str) -> None:
        self.increment(f"{service_name}_errors")

    def record_external_skip(self, service_name: str) -> None:
        self.increment(f"{service_name}_skipped")

    def snapshot(self) -> dict[str, Mapping[str, int]]:
        with self._lock:
            return {
                "counters": dict(sorted(self._counters.items())),
                "labels": dict(sorted(self._labels.items())),
                "sources": dict(sorted(self._sources.items())),
            }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()
            self._labels.clear()
            self._sources.clear()


DIAGNOSTICS = DiagnosticsStore()


def clear_diagnostics() -> None:
    DIAGNOSTICS.clear()
