"""Workflow translation module with caching and legal-safety prompt controls."""


from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from collections import deque
from uuid import uuid4
from typing import Final

from config import TRANSLATION_CB_COOLDOWN, TRANSLATION_CB_THRESHOLD, TRANSLATION_RETRIES, TRANSLATION_TIMEOUT
from openai import OpenAI

from .legal_dictionary import apply_legal_dictionary
from .translation_cache import get_cached_translation, get_cache_entry_count, store_translation
from .translation_validator import enforce_valid_translation, validate_translation

logger = logging.getLogger(__name__)

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, list[str]]] = {}
_CACHE_TTL_SECONDS: Final[int] = 60 * 60 * 6  # 6 hours
_CACHE_MAX_ENTRIES: Final[int] = 500
_RECENT_ERRORS: deque[str] = deque(maxlen=20)

_CB_LOCK = threading.Lock()
_CIRCUIT_OPEN_UNTIL = 0.0
_CONSECUTIVE_FAILURES = 0

_TARGET_LANGUAGE_NAMES: Final[dict[str, str]] = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}


def _get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _cache_key(category: str, language: str) -> str:
    return f"{category.strip().lower()}::{language.strip().lower()}"


def _cleanup_cache_if_needed() -> None:
    if len(_CACHE) <= _CACHE_MAX_ENTRIES:
        return
    # Drop oldest 10% entries when size threshold is crossed.
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


def _is_circuit_open() -> bool:
    with _CB_LOCK:
        return time.time() < _CIRCUIT_OPEN_UNTIL


def _register_success() -> None:
    global _CONSECUTIVE_FAILURES, _CIRCUIT_OPEN_UNTIL
    with _CB_LOCK:
        _CONSECUTIVE_FAILURES = 0
        _CIRCUIT_OPEN_UNTIL = 0.0


def _register_failure(cooldown_seconds: float, threshold: int) -> None:
    global _CONSECUTIVE_FAILURES, _CIRCUIT_OPEN_UNTIL
    with _CB_LOCK:
        _CONSECUTIVE_FAILURES += 1
        if _CONSECUTIVE_FAILURES >= max(1, threshold):
            _CIRCUIT_OPEN_UNTIL = time.time() + max(1.0, cooldown_seconds)


def _coerce_steps(translated: object, expected_count: int) -> list[str] | None:
    if not isinstance(translated, list):
        return None
    cleaned = [str(step).strip() for step in translated if str(step).strip()]
    if len(cleaned) != expected_count:
        return None
    return cleaned


def _backoff_delay_seconds(attempt_index: int) -> float:
    base = 0.4 * (2 ** attempt_index)
    jitter = random.uniform(0.0, 0.25)
    return min(3.0, base + jitter)


def _normalize_input_steps(workflow_text: str | list[str]) -> list[str]:
    if isinstance(workflow_text, list):
        return [str(step).strip() for step in workflow_text if str(step).strip()]
    text = str(workflow_text or "").strip()
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def _register_recent_error(error: Exception | str) -> None:
    _RECENT_ERRORS.appendleft(str(error))


def get_translation_health() -> dict[str, object]:
    """Health payload used by AI health endpoint."""
    return {
        "translation_status": "open_circuit" if _is_circuit_open() else "ok",
        "cache_entries": get_cache_entry_count(),
        "recent_errors": list(_RECENT_ERRORS),
    }


def translate_workflow(
    workflow_text: str | list[str],
    target_language: str,
    category: str = "Unknown",
    request_id: str | None = None,
) -> tuple[list[str], bool, bool]:
    """
    Translate workflow steps into target language in one batch call.

    Returns:
        (localized_steps, translation_triggered, cache_hit)
    """
    workflow_steps = _normalize_input_steps(workflow_text)
    if not workflow_steps:
        return [], False, False

    lang = (target_language or "en").lower()
    if lang == "en":
        return list(workflow_steps), False, False

    if lang not in {"hi", "mr"}:
        return list(workflow_steps), False, False

    cache_key = _cache_key(category=category or "unknown", language=lang)
    cached = _read_cache(cache_key)
    if cached is not None:
        logger.info("Workflow translation cache hit | category=%s language=%s", category, lang)
        return cached, False, True

    persistent_cached = get_cached_translation(category=category, language=lang)
    if persistent_cached is not None:
        _write_cache(cache_key, persistent_cached)
        logger.info("Workflow translation persistent cache hit | category=%s language=%s", category, lang)
        return persistent_cached, False, True

    if _is_circuit_open():
        logger.warning("Translation skipped due to open circuit breaker | category=%s language=%s", category, lang)
        return list(workflow_steps), False, False

    client = _get_openai_client()
    if client is None:
        logger.warning("Translation skipped due to missing OPENAI_API_KEY")
        return list(workflow_steps), False, False

    timeout = max(2.0, float(TRANSLATION_TIMEOUT))
    retries = max(0, int(TRANSLATION_RETRIES))
    failure_threshold = int(TRANSLATION_CB_THRESHOLD)
    cooldown_seconds = float(TRANSLATION_CB_COOLDOWN)

    system_prompt = (
        "You translate legal procedural guidance for citizens. "
        "Output strict JSON with key translated_steps (array of strings). "
        "Rules: preserve legal meaning, keep structure and order exactly, "
        "do not add/remove steps, use simple citizen language, and keep legal terms accurate. "
        "Keep numbering/bullet markers unchanged."
    )

    language_name = _TARGET_LANGUAGE_NAMES.get(lang, "Hindi")
    source_text = "\n".join(workflow_steps)
    glossary_applied = apply_legal_dictionary(source_text, lang)

    payload = {
        "category": category,
        "target_language": language_name,
        "steps": workflow_steps,
        "dictionary_adjusted_text": glossary_applied,
    }
    user_prompt = (
        f"Translate this procedural legal guidance into {language_name}.\n"
        "Keep numbering and order consistent.\n"
        "Return valid JSON only.\n"
        f"Input JSON:\n{json.dumps(payload, ensure_ascii=True)}"
    )

    request_tag = request_id or str(uuid4())
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0.2,
                response_format={"type": "json_object"},
                timeout=timeout,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (response.choices[0].message.content or "").strip().replace("```json", "").replace("```", "")
            output = json.loads(content)
            translated = output.get("translated_steps", [])
            translated_steps = _coerce_steps(translated, expected_count=len(workflow_steps))
            if translated_steps is not None:
                safe_steps = enforce_valid_translation(workflow_steps, translated_steps)
                if not validate_translation(workflow_steps, safe_steps):
                    raise ValueError("Translation validation failed")

                _write_cache(cache_key, safe_steps)
                store_translation(category=category, language=lang, text=safe_steps)
                _register_success()
                logger.info(
                    "Workflow translation complete | request_id=%s category=%s language=%s",
                    request_tag,
                    category,
                    lang,
                )
                return safe_steps, True, False

            raise ValueError("Translated steps missing or structure mismatch")
        except Exception as exc:
            last_error = exc
            _register_recent_error(exc)
            _register_failure(cooldown_seconds=cooldown_seconds, threshold=failure_threshold)
            logger.warning(
                "Workflow translation failed (request_id=%s attempt=%s/%s) | category=%s language=%s error=%s",
                request_tag,
                attempt + 1,
                retries + 1,
                category,
                lang,
                exc,
            )
            if attempt < retries:
                time.sleep(_backoff_delay_seconds(attempt))

    logger.error("Workflow translation fallback used | category=%s language=%s error=%s", category, lang, last_error)
    return list(workflow_steps), False, False


from ai_engine.openai_service import get_openai_client

client = get_openai_client()

def translate(text):

    response = client.chat.completions.create(

        model="gpt-4.1-mini",

        messages=[
        {"role":"user","content":text}
        ]

    )

    return response.choices[0].message.content
