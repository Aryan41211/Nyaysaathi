"""Runtime observability and alerting utilities for NyaySaathi API pipeline."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from typing import Any

from utils.logger import get_logger

logger = get_logger("legal.monitoring")


class RuntimeObservability:
    """Collects query-level decisions, rates, and emits alert conditions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._window_seconds = max(60, int(os.getenv("OBS_WINDOW_SECONDS", "300")))
        self._low_confidence_alert_rate = float(os.getenv("ALERT_LOW_CONF_RATE", "0.45"))
        self._error_alert_rate = float(os.getenv("ALERT_ERROR_RATE", "0.12"))
        self._fallback_alert_rate = float(os.getenv("ALERT_FALLBACK_RATE", "0.35"))
        self._events: deque[dict[str, Any]] = deque(maxlen=4000)
        self._feedback_total = 0
        self._feedback_positive = 0
        self._feedback_negative = 0

    def _evict_old(self, now: float) -> None:
        while self._events and (now - float(self._events[0].get("ts", now))) > self._window_seconds:
            self._events.popleft()

    def record_decision(
        self,
        *,
        query: str,
        normalized_query: str,
        intent: str,
        confidence: str,
        decision: str,
        cache_hit: bool,
        fallback: bool,
        latency_ms: float,
    ) -> None:
        confidence_norm = str(confidence or "Low").strip().lower()
        now = time.time()
        event = {
            "ts": now,
            "type": "decision",
            "query": str(query or ""),
            "normalized_query": str(normalized_query or query or ""),
            "intent": str(intent or "General legal issue"),
            "confidence": confidence_norm,
            "decision": str(decision or "fallback"),
            "cache_hit": bool(cache_hit),
            "fallback": bool(fallback),
            "latency_ms": round(float(latency_ms or 0.0), 2),
        }
        with self._lock:
            self._events.append(event)
            self._evict_old(now)

        logger.info(json.dumps({"event": "pipeline_decision", **event}, ensure_ascii=True))

    def record_error(self, error_type: str) -> None:
        now = time.time()
        event = {
            "ts": now,
            "type": "error",
            "error_type": str(error_type or "unknown_error"),
        }
        with self._lock:
            self._events.append(event)
            self._evict_old(now)

        logger.error(json.dumps({"event": "pipeline_error", **event}, ensure_ascii=True))

    def record_feedback(self, positive: bool) -> None:
        with self._lock:
            self._feedback_total += 1
            if positive:
                self._feedback_positive += 1
            else:
                self._feedback_negative += 1

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            self._evict_old(now)
            events = list(self._events)
            total = max(1, len(events))
            decisions = [e for e in events if e.get("type") == "decision"]
            decision_total = max(1, len(decisions))
            error_count = sum(1 for e in events if e.get("type") == "error")
            fallback_count = sum(1 for e in decisions if bool(e.get("fallback", False)))
            low_conf_count = sum(1 for e in decisions if str(e.get("confidence", "")).lower() == "low")
            cache_hits = sum(1 for e in decisions if bool(e.get("cache_hit", False)))
            avg_latency = (
                sum(float(e.get("latency_ms", 0.0)) for e in decisions) / decision_total
                if decisions
                else 0.0
            )

            feedback_accuracy = (
                round(self._feedback_positive / max(1, self._feedback_total), 4) if self._feedback_total else None
            )

            low_conf_rate = low_conf_count / decision_total
            error_rate = error_count / total
            fallback_rate = fallback_count / decision_total

            alerts = []
            if low_conf_rate >= self._low_confidence_alert_rate:
                alerts.append(
                    {
                        "type": "low_confidence_rate",
                        "severity": "warning",
                        "value": round(low_conf_rate, 4),
                        "threshold": self._low_confidence_alert_rate,
                    }
                )
            if error_rate >= self._error_alert_rate:
                alerts.append(
                    {
                        "type": "error_rate_spike",
                        "severity": "critical",
                        "value": round(error_rate, 4),
                        "threshold": self._error_alert_rate,
                    }
                )
            if fallback_rate >= self._fallback_alert_rate:
                alerts.append(
                    {
                        "type": "fallback_rate",
                        "severity": "warning",
                        "value": round(fallback_rate, 4),
                        "threshold": self._fallback_alert_rate,
                    }
                )

            return {
                "window_seconds": self._window_seconds,
                "total_events": len(events),
                "decision_events": len(decisions),
                "error_events": error_count,
                "fallback_rate": round(fallback_rate, 4),
                "low_confidence_rate": round(low_conf_rate, 4),
                "error_rate": round(error_rate, 4),
                "cache_hit_rate": round(cache_hits / decision_total, 4),
                "avg_latency_ms": round(avg_latency, 2),
                "feedback_accuracy": feedback_accuracy,
                "feedback_total": self._feedback_total,
                "alerts": alerts,
            }


_OBSERVABILITY = RuntimeObservability()


def get_observability() -> RuntimeObservability:
    return _OBSERVABILITY
