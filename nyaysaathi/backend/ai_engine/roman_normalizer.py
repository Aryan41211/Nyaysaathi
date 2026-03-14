"""Roman-script normalization module for Hindi/Marathi legal queries."""
from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Final

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)
_OPENAI_DISABLED_UNTIL = 0.0


def _openai_temporarily_disabled() -> bool:
    return time.time() < _OPENAI_DISABLED_UNTIL


def _mark_quota_exhausted(cooldown_seconds: float = 900.0) -> None:
    global _OPENAI_DISABLED_UNTIL
    _OPENAI_DISABLED_UNTIL = time.time() + max(60.0, cooldown_seconds)

_ROMAN_RE = re.compile(r"^[\x00-\x7F\s\d\W]+$")

# Minimal deterministic cleanup before AI normalization.
_REPLACEMENTS: Final[dict[str, str]] = {
    "plz": "please",
    "fir": "FIR",
    "paisa": "money",
    "polise": "police",
    "shikayat": "complaint",
}


def _is_roman_text(text: str) -> bool:
    return bool(_ROMAN_RE.match(text or ""))


def _light_cleanup(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    lowered = cleaned.lower()
    for src, dst in _REPLACEMENTS.items():
        lowered = lowered.replace(src, dst)
    return lowered


def _get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "")
    if not api_key or _openai_temporarily_disabled():
        return None
    return OpenAI(api_key=api_key)


def normalize_roman_text(user_input: str, language: str) -> str:
    """
    Normalize Roman Hindi/Marathi to cleaner text for intent classification.

    Behavior:
    - For `en`: return cleaned English text.
    - For `hi`/`mr` Roman text: AI-assisted normalization if API key exists.
    - Fallback to deterministic cleanup if API unavailable/errors.
    """
    text = (user_input or "").strip()
    if not text:
        return ""

    cleaned = _light_cleanup(text)
    if language == "en" or not _is_roman_text(cleaned):
        return cleaned

    if language not in {"hi", "mr"}:
        return cleaned

    client = _get_openai_client()
    if client is None:
        return cleaned

    timeout = max(2.0, float(getattr(settings, "OPENAI_NORMALIZER_TIMEOUT", 8.0)))
    retries = max(0, int(getattr(settings, "OPENAI_NORMALIZER_RETRIES", 1)))

    system_prompt = (
        "You normalize Roman-script Hindi/Marathi legal complaints into native script. "
        "For language=hi return Devanagari Hindi, for language=mr return Devanagari Marathi. "
        "Return strict JSON with one key: normalized_text. "
        "Keep user meaning exact and concise. Do not add facts."
    )
    user_prompt = (
        f"language={language}\n"
        "Normalize this Roman text for legal intent classification:\n"
        f"{cleaned}"
    )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=timeout,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = (response.choices[0].message.content or "").strip().replace("```json", "").replace("```", "")
            payload = json.loads(content)
            normalized = str(payload.get("normalized_text", "")).strip()
            if normalized:
                return normalized
            raise ValueError("normalized_text missing from model response")
        except Exception as exc:
            lowered = str(exc).lower()
            if (
                "insufficient_quota" in lowered
                or "insufficient quota" in lowered
                or "error code: 429" in lowered
            ):
                _mark_quota_exhausted()
            last_error = exc
            logger.warning(
                "Roman normalization failed (attempt=%s/%s): %s",
                attempt + 1,
                retries + 1,
                exc,
            )
            if attempt < retries:
                time.sleep(min(1.8, (0.35 * (2 ** attempt)) + random.uniform(0.0, 0.2)))

    logger.warning("Roman normalization fallback used after retries: %s", last_error)
    return cleaned


def normalize_text(text: str, language: str | None = None) -> str:
    """Compatibility entrypoint requested by multilingual pipeline spec."""
    if language is None:
        from .language_detector import detect_language

        detected = detect_language(text)
    else:
        detected = language

    if detected == "en":
        return _light_cleanup(text)
    return normalize_roman_text(text, detected)

