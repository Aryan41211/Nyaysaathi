"""Input normalization helpers for multilingual legal queries."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .language_detector import detect_language
from .openai_service import get_openai_client

logger = logging.getLogger(__name__)

_ROMAN_HINT_RE = re.compile(
    r"\b(mera|meri|mujhe|nahi|mila|gharath|gharat|zali|pagar|paisa|majha|majhi)\b",
    re.IGNORECASE,
)


def _needs_ai_normalization(text: str, language: str) -> bool:
    if language in {"hi", "mr"}:
        return True
    if _ROMAN_HINT_RE.search(text):
        return True
    return False


def normalize_user_input(
    text: str,
    preferred_language: str | None = None,
    allow_ai: bool = True,
) -> tuple[str, str, bool]:
    """
    Normalize user text and optionally convert Roman Hindi/Marathi into native script.

    Returns:
        (normalized_text, detected_language, used_ai)
    """
    source_text = (text or "").strip()
    if not source_text:
        return "", "en", False

    detected = (preferred_language or "").strip().lower() or detect_language(source_text)
    if not allow_ai or not _needs_ai_normalization(source_text, detected):
        return source_text, detected, False

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.0,
            response_format={"type": "json_object"},
            timeout=8,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You normalize multilingual legal queries. "
                        "Detect language (en/hi/mr), convert Roman Hindi/Marathi to native script, "
                        "fix obvious spelling noise, and keep legal meaning unchanged. "
                        "Return strict JSON with keys language and normalized_text only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "text": source_text,
                            "hint_language": detected,
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
        )
        payload = json.loads((response.choices[0].message.content or "").strip())
        normalized_text = str(payload.get("normalized_text", source_text)).strip() or source_text
        lang = str(payload.get("language", detected)).strip().lower()
        if lang not in {"en", "hi", "mr"}:
            lang = detected
        return normalized_text, lang, True
    except Exception as exc:
        logger.warning("normalize_user_input fallback used: %s", exc)
        return source_text, detected, False


def normalize(text: str) -> str:
    """Backward-compatible wrapper used by older call sites."""
    normalized, _, _ = normalize_user_input(text)
    return normalized
