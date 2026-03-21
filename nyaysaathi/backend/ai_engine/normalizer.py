"""Input normalization helpers for multilingual legal queries."""

from __future__ import annotations

import logging
import re

from .language_detector import detect_language

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
    if _needs_ai_normalization(source_text, detected):
        logger.debug("Using local normalization path for potentially noisy roman text")

    # Local deterministic cleanup only; no remote model dependency.
    normalized_text = " ".join(source_text.split())
    return normalized_text, detected, False


def normalize(text: str) -> str:
    """Backward-compatible wrapper used by older call sites."""
    normalized, _, _ = normalize_user_input(text)
    return normalized
