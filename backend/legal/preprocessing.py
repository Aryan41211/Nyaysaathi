"""Lightweight text preprocessing utilities for semantic matching quality."""

from __future__ import annotations

import re

STOP_WORDS = {
    "the",
    "is",
    "my",
    "a",
    "an",
    "and",
    "of",
    "to",
    "for",
    "in",
    "on",
    "at",
    "with",
    "has",
    "have",
    "had",
}

_NUMBER_MAP = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
    "10": "ten",
}

try:
    from nltk.stem import PorterStemmer  # type: ignore

    _STEMMER: PorterStemmer | None = PorterStemmer()
except Exception:  # noqa: BLE001
    _STEMMER = None


def normalize_text(text: str) -> str:
    """Lowercase, remove punctuation, normalize spaces, and map small numbers."""
    lowered = (text or "").lower().strip()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    tokens = [_NUMBER_MAP.get(token, token) for token in lowered.split()]
    return " ".join(tokens).strip()


def remove_stopwords(text: str) -> str:
    """Remove simple stopwords to reduce noise in embedding similarity."""
    tokens = [token for token in (text or "").split() if token not in STOP_WORDS]
    return " ".join(tokens).strip()


def _stem_text(text: str) -> str:
    if _STEMMER is None:
        return text
    tokens = [_STEMMER.stem(token) for token in (text or "").split()]
    return " ".join(tokens).strip()


def clean_text(text: str) -> str:
    """Main preprocessing pipeline used before all embedding generation."""
    normalized = normalize_text(text)
    no_stopwords = remove_stopwords(normalized)
    stemmed = _stem_text(no_stopwords)
    return re.sub(r"\s+", " ", stemmed).strip()
