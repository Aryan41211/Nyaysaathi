"""In-process monitoring utilities for NyaySaathi AI understanding pipeline."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any


class AIMonitor:
    """Thread-safe runtime metrics collector for AI understanding operations."""

    def __init__(self, snapshot_every: int = 25) -> None:
        self._lock = threading.Lock()
        self._snapshot_every = max(1, int(snapshot_every))
        self._started_at = time.time()

        self._total_requests = 0
        self._success_count = 0
        self._fallback_count = 0
        self._failure_count = 0
        self._total_retries_used = 0
        self._clarification_count = 0
        self._low_confidence_count = 0
        self._latency_sum_ms = 0.0

        self._category_counts: dict[str, int] = defaultdict(int)
        self._last_error: str = ""

    def record_success(
        self,
        *,
        category: str,
        confidence: float,
        clarification_required: bool,
        retries_used: int,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self._total_requests += 1
            self._success_count += 1
            self._total_retries_used += max(0, retries_used)
            self._latency_sum_ms += max(0.0, latency_ms)
            self._category_counts[category or "Unknown"] += 1

            if clarification_required:
                self._clarification_count += 1
            if confidence < 0.55:
                self._low_confidence_count += 1

    def record_fallback(self, *, error_type: str, retries_used: int, latency_ms: float) -> None:
        with self._lock:
            self._total_requests += 1
            self._fallback_count += 1
            self._failure_count += 1
            self._total_retries_used += max(0, retries_used)
            self._latency_sum_ms += max(0.0, latency_ms)
            self._last_error = error_type

    def should_emit_snapshot(self) -> bool:
        with self._lock:
            return self._total_requests > 0 and self._total_requests % self._snapshot_every == 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total = max(1, self._total_requests)
            uptime_s = time.time() - self._started_at
            return {
                "uptime_seconds": round(uptime_s, 2),
                "total_requests": self._total_requests,
                "success_count": self._success_count,
                "fallback_count": self._fallback_count,
                "failure_count": self._failure_count,
                "success_rate": round(self._success_count / total, 4),
                "fallback_rate": round(self._fallback_count / total, 4),
                "avg_latency_ms": round(self._latency_sum_ms / total, 2),
                "avg_retries_used": round(self._total_retries_used / total, 2),
                "clarification_rate": round(self._clarification_count / total, 4),
                "low_confidence_rate": round(self._low_confidence_count / total, 4),
                "top_categories": dict(sorted(self._category_counts.items(), key=lambda item: item[1], reverse=True)[:6]),
                "last_error": self._last_error,
            }
