"""AI orchestration facade for NyaySaathi legal understanding pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from uuid import uuid4
from typing import Any

from django.conf import settings
from openai import APITimeoutError, RateLimitError

from .confidence_engine import ConfidenceEngine
from .fallback_engine import FallbackEngine, attach_legacy_aliases
from .intent_engine import AIUnderstandingError, IntentEngine, get_openai_client
from .monitoring import AIMonitor
from .prompt_manager import get_example_test_inputs as _get_example_test_inputs

logger = logging.getLogger(__name__)
monitor_logger = logging.getLogger("legal.monitoring")


_AI_MONITOR = AIMonitor(snapshot_every=int(getattr(settings, "AI_MONITOR_SNAPSHOT_EVERY", 25)))
_OPENAI_DISABLED_UNTIL = 0.0


def _is_openai_temporarily_disabled() -> bool:
    return time.time() < _OPENAI_DISABLED_UNTIL


def _mark_openai_quota_exhausted(cooldown_seconds: float = 900.0) -> None:
    global _OPENAI_DISABLED_UNTIL
    _OPENAI_DISABLED_UNTIL = time.time() + max(60.0, cooldown_seconds)


def _input_fingerprint(text: str) -> str:
    """Generate non-reversible fingerprint to trace requests without logging raw text."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _emit_event(level: str, event: str, payload: dict[str, Any]) -> None:
    """Emit structured JSON logs for observability pipelines."""
    message = json.dumps({"event": event, **payload}, ensure_ascii=True)
    if level == "error":
        monitor_logger.error(message)
    elif level == "warning":
        monitor_logger.warning(message)
    else:
        monitor_logger.info(message)


def _should_retry(error: Exception) -> bool:
    """Identify transient failures safe for retry."""
    err_text = str(error).lower()
    if "insufficient_quota" in err_text or "insufficient quota" in err_text:
        return False

    if isinstance(error, RateLimitError):
        return False

    if isinstance(error, APITimeoutError):
        return True

    text = err_text
    transient_markers = ("timeout", "temporar", "rate limit", "connection", "503", "502", "429")
    return any(marker in text for marker in transient_markers)


def _backoff_delay_seconds(attempt_index: int) -> float:
    """Exponential backoff with jitter for resilient upstream calls."""
    base = 0.5 * (2 ** attempt_index)
    jitter = random.uniform(0.0, 0.35)
    return min(4.0, base + jitter)


def _enforce_clarification_policy(result: dict[str, Any], user_input: str) -> dict[str, Any]:
    """Ensure clarification behavior is consistent for low-confidence outcomes."""
    output = dict(result)
    confidence = float(output.get("confidence", 0.25))
    if confidence < 0.55:
        output["clarification_required"] = True

    if output.get("clarification_required"):
        output["clarification_questions"] = FallbackEngine.generate_clarification_questions(output, user_input)

    return output


def understand_user_problem(user_input: str) -> dict[str, Any]:
    """
    Understand a natural-language legal problem using a modular AI pipeline.

    Pipeline:
      1. Intent engine call (OpenAI + prompt manager + response validator)
      2. Fallback engine policy (non-legal detection + clarification rules)
      3. Confidence engine calibration
      4. Legacy alias attachment for existing API consumers
    """
    text = (user_input or "").strip()
    request_id = str(uuid4())
    started = time.perf_counter()

    if _is_openai_temporarily_disabled():
        return attach_legacy_aliases(FallbackEngine.build_error_fallback(text))

    if not text:
        fallback = attach_legacy_aliases(FallbackEngine.build_error_fallback(""))
        elapsed_ms = (time.perf_counter() - started) * 1000
        _AI_MONITOR.record_fallback(error_type="empty_input", retries_used=0, latency_ms=elapsed_ms)
        _emit_event(
            "warning",
            "ai_understanding_fallback",
            {
                "request_id": request_id,
                "reason": "empty_input",
                "latency_ms": round(elapsed_ms, 2),
            },
        )
        return fallback

    retries = max(0, int(getattr(settings, "OPENAI_UNDERSTANDING_RETRIES", 2)))
    timeout = max(2.0, float(getattr(settings, "OPENAI_UNDERSTANDING_TIMEOUT", 10.0)))

    try:
        client = get_openai_client()
    except AIUnderstandingError as error:
        logger.error("AI client configuration error: %s", error)
        elapsed_ms = (time.perf_counter() - started) * 1000
        _AI_MONITOR.record_fallback(
            error_type="client_config_error",
            retries_used=0,
            latency_ms=elapsed_ms,
        )
        _emit_event(
            "error",
            "ai_understanding_fallback",
            {
                "request_id": request_id,
                "reason": "client_config_error",
                "input_fp": _input_fingerprint(text),
                "input_len": len(text),
                "latency_ms": round(elapsed_ms, 2),
            },
        )
        return attach_legacy_aliases(FallbackEngine.build_error_fallback(text))

    engine = IntentEngine(client=client)
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            result = engine.understand(user_input=text, timeout=timeout)
            result = FallbackEngine.apply_fallback_rules(result, user_input=text)
            result["confidence"] = ConfidenceEngine.calibrate(result, user_input=text)
            result = _enforce_clarification_policy(result, user_input=text)

            elapsed_ms = (time.perf_counter() - started) * 1000
            _AI_MONITOR.record_success(
                category=str(result.get("category", "Unknown")),
                confidence=float(result.get("confidence", 0.25)),
                clarification_required=bool(result.get("clarification_required", False)),
                retries_used=attempt,
                latency_ms=elapsed_ms,
            )
            _emit_event(
                "info",
                "ai_understanding_success",
                {
                    "request_id": request_id,
                    "input_fp": _input_fingerprint(text),
                    "input_len": len(text),
                    "category": result.get("category", "Other"),
                    "confidence": round(float(result.get("confidence", 0.0)), 3),
                    "clarification_required": bool(result.get("clarification_required", False)),
                    "retries_used": attempt,
                    "latency_ms": round(elapsed_ms, 2),
                },
            )
            if _AI_MONITOR.should_emit_snapshot():
                _emit_event("info", "ai_monitor_snapshot", _AI_MONITOR.snapshot())

            return attach_legacy_aliases(result)
        except Exception as error:
            last_error = error
            lowered_error = str(error).lower()
            if (
                "insufficient_quota" in lowered_error
                or "insufficient quota" in lowered_error
                or "error code: 429" in lowered_error
            ):
                _mark_openai_quota_exhausted()
            retryable = _should_retry(error)
            logger.warning(
                "understand_user_problem failed (attempt=%s/%s, retryable=%s): %s",
                attempt + 1,
                retries + 1,
                retryable,
                error,
            )

            if attempt < retries and retryable:
                time.sleep(_backoff_delay_seconds(attempt))
                continue
            break

    logger.error("AI understanding fallback used after failure: %s", last_error)
    elapsed_ms = (time.perf_counter() - started) * 1000
    _AI_MONITOR.record_fallback(
        error_type=type(last_error).__name__ if last_error else "unknown_error",
        retries_used=retries,
        latency_ms=elapsed_ms,
    )
    _emit_event(
        "error",
        "ai_understanding_fallback",
        {
            "request_id": request_id,
            "reason": type(last_error).__name__ if last_error else "unknown_error",
            "input_fp": _input_fingerprint(text),
            "input_len": len(text),
            "retries_used": retries,
            "latency_ms": round(elapsed_ms, 2),
        },
    )
    if _AI_MONITOR.should_emit_snapshot():
        _emit_event("info", "ai_monitor_snapshot", _AI_MONITOR.snapshot())
    return attach_legacy_aliases(FallbackEngine.build_error_fallback(text))


def get_example_test_inputs() -> list[str]:
    """Expose sample inputs for QA/testing without duplicating fixtures."""
    return _get_example_test_inputs()


def get_ai_monitoring_snapshot() -> dict[str, Any]:
    """Return current in-process AI monitoring snapshot."""
    return _AI_MONITOR.snapshot()
