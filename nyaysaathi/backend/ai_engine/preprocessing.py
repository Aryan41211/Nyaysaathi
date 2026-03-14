"""Text preprocessing utilities for semantic legal understanding."""
from __future__ import annotations

import re

from .roman_normalizer import normalize_text

_NOISE_RE = re.compile(r"[^\w\s\u0900-\u097F]")
_MULTI_SPACE_RE = re.compile(r"\s+")


def preprocess_text(text: str, language: str | None = None) -> str:
    """Normalize user text for semantic embedding and retrieval."""
    raw = (text or "").strip()
    if not raw:
        return ""

    lowered = raw.lower()
    cleaned = _NOISE_RE.sub(" ", lowered)
    compact = _MULTI_SPACE_RE.sub(" ", cleaned).strip()
    return normalize_text(compact, language=language)

