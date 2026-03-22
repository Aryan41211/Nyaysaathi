"""Compatibility facade for language processing."""

from .language_detector import detect_language
from .normalizer import normalize, normalize_user_input
from .roman_normalizer import normalize_text as normalize_roman_text

__all__ = ["detect_language", "normalize", "normalize_user_input", "normalize_roman_text"]
