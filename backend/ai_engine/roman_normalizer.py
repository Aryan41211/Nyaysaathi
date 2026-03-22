"""Roman-script normalization module with local deterministic cleanup only."""

from __future__ import annotations

import re
from typing import Final

_ROMAN_RE = re.compile(r"^[\x00-\x7F\s\d\W]+$")

_REPLACEMENTS: Final[dict[str, str]] = {
    "plz": "please",
    "polise": "police",
    "shikayat": "complaint",
    "paisa": "money",
}


def _is_roman_text(text: str) -> bool:
    return bool(_ROMAN_RE.match(text or ""))


def _light_cleanup(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    lowered = cleaned.lower()
    for src, dst in _REPLACEMENTS.items():
        lowered = lowered.replace(src, dst)
    return lowered


def normalize_roman_text(user_input: str, language: str) -> str:
    """Normalize Roman Hindi/Marathi text using local deterministic rules."""
    text = (user_input or "").strip()
    if not text:
        return ""

    cleaned = _light_cleanup(text)
    if language == "en":
        return cleaned

    if language in {"hi", "mr"} and _is_roman_text(cleaned):
        return cleaned

    return cleaned


def normalize_text(text: str, language: str | None = None) -> str:
    """Compatibility entrypoint for multilingual pipeline."""
    if language is None:
        from .language_detector import detect_language

        detected = detect_language(text)
    else:
        detected = language

    return normalize_roman_text(text, detected)

