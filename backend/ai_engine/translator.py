"""Workflow translation module with local fallback-only behavior."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Final

from .translation_cache import get_cache_entry_count

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL_SECONDS: Final[int] = 60 * 60 * 6
_CACHE_MAX_ENTRIES: Final[int] = 500
_RECENT_ERRORS: deque[str] = deque(maxlen=20)


_TARGET_LANGUAGE_NAMES: Final[dict[str, str]] = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def _cache_key(category: str, language: str) -> str:
    return f"{category.strip().lower()}::{language.strip().lower()}"


def _cleanup_cache_if_needed() -> None:
    if len(_CACHE) <= _CACHE_MAX_ENTRIES:
        return
    to_drop = max(1, int(_CACHE_MAX_ENTRIES * 0.1))
    oldest_keys = sorted(_CACHE.keys(), key=lambda key: _CACHE[key][0])[:to_drop]
    for key in oldest_keys:
        _CACHE.pop(key, None)


def _read_cache(key: str) -> list[str] | None:
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if not item:
            return None
        ts, value = item
        if (time.time() - ts) > _CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        return list(value)


def _write_cache(key: str, value: list[str]) -> None:
    with _CACHE_LOCK:
        _cleanup_cache_if_needed()
        _CACHE[key] = (time.time(), list(value))


def _normalize_input_steps(workflow_text: str | list[str]) -> list[str]:
    if isinstance(workflow_text, list):
        return [str(step).strip() for step in workflow_text if str(step).strip()]
    text = str(workflow_text or "").strip()
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_translation_health() -> dict[str, object]:
    """Health payload used by AI health endpoint."""
    return {
        "translation_status": "local_only",
        "cache_entries": get_cache_entry_count(),
        "recent_errors": list(_RECENT_ERRORS),
    }


def translate_workflow(
    workflow_text: str | list[str],
    target_language: str,
    category: str = "Unknown",
    request_id: str | None = None,
) -> tuple[list[str], bool, bool]:
    """Return source workflow because local build has no machine translation dependency."""
    del request_id

    workflow_steps = _normalize_input_steps(workflow_text)
    if not workflow_steps:
        return [], False, False

    lang = (target_language or "en").lower()
    if lang not in _TARGET_LANGUAGE_NAMES:
        return list(workflow_steps), False, False

    cache_key = _cache_key(category=category or "unknown", language=lang)
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached, False, True

    _write_cache(cache_key, workflow_steps)
    return list(workflow_steps), False, False
