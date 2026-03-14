"""Language detection module for NyaySaathi multilingual pipeline."""
from __future__ import annotations

import logging
import re
from typing import Final

from config import LANG_DETECT_MIN_CONFIDENCE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Strong Marathi signal terms typically written in Roman script.
_MARATHI_ROMAN_HINTS: Final[tuple[str, ...]] = (
    "aahe",
    "zali",
    "ghar",
    "gharat",
    "majha",
    "majhi",
    "mala",
    "milala",
    "pagar",
    "paisa",
    "nahi",
    "karaycha",
)

# Hindi signal terms commonly seen in Roman script.
_HINDI_ROMAN_HINTS: Final[tuple[str, ...]] = (
    "mera",
    "meri",
    "kya",
    "mila",
    "shikayat",
    "kaise",
)

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def _detect_devanagari_variant(text: str) -> str:
    """Heuristic split between Hindi/Marathi when input is in Devanagari."""
    lowered = text.lower()
    marathi_signals = (
        "\u0906\u0939\u0947",  # आहे
        "\u091d\u093e\u0932\u0940",  # झाली
        "\u092e\u093e\u091d",  # माझ
        "\u0928\u093e\u0939\u0940",  # नाही
        "\u0918\u0930\u093e\u0924",  # घरात
    )
    hindi_signals = (
        "\u0939\u0948",  # है
        "\u0928\u0939\u0940\u0902",  # नहीं
        "\u092e\u0947\u0930\u093e",  # मेरा
        "\u092e\u0947\u0930\u0940",  # मेरी
        "\u0915\u0943\u092a\u092f\u093e",  # कृपया
    )

    marathi_hits = sum(1 for token in marathi_signals if token in text or token in lowered)
    hindi_hits = sum(1 for token in hindi_signals if token in text or token in lowered)

    if marathi_hits > hindi_hits:
        return "mr"
    if hindi_hits > marathi_hits:
        return "hi"
    return "hi"


def _detect_roman_variant(text: str) -> str:
    lowered = text.lower()
    marathi_hits = sum(1 for token in _MARATHI_ROMAN_HINTS if token in lowered)
    hindi_hits = sum(1 for token in _HINDI_ROMAN_HINTS if token in lowered)

    if marathi_hits >= 1 and marathi_hits >= hindi_hits:
        return "mr"
    if hindi_hits > marathi_hits:
        return "hi"
    return "en"


def detect_language(user_input: str) -> str:
    """
    Detect input language and normalize to one of: en, hi, mr.

    Uses `langdetect` when available and falls back to deterministic heuristics.
    """
    text = (user_input or "").strip()
    if not text:
        return "en"

    try:
        if _DEVANAGARI_RE.search(text):
            detected = _detect_devanagari_variant(text)
            logger.info("Language detected via Devanagari heuristic: %s", detected)
            return detected

        roman_guess = _detect_roman_variant(text)

        try:
            from langdetect import detect_langs  # type: ignore

            candidates = detect_langs(text)
            if candidates:
                top = candidates[0]
                top_lang = str(getattr(top, "lang", "en"))
                top_prob = float(getattr(top, "prob", 0.0))

                if top_prob < LANG_DETECT_MIN_CONFIDENCE:
                    logger.info(
                        "Language confidence low (%.3f), fallback=%s",
                        top_prob,
                        roman_guess,
                    )
                    return roman_guess

                if top_lang in SUPPORTED_LANGUAGES:
                    if top_lang == "en" and roman_guess in {"hi", "mr"}:
                        logger.info("Language corrected via roman heuristic override: %s", roman_guess)
                        return roman_guess
                    logger.info("Language detected via langdetect: %s (%.3f)", top_lang, top_prob)
                    return top_lang
                if top_lang == "ne":
                    # Common confusion for Marathi/Hindi regional text; fallback to roman heuristics.
                    logger.info("Language detected via langdetect fallback (ne -> %s)", roman_guess)
                    return roman_guess
        except Exception:
            # langdetect not installed or failed on very short input.
            pass

        logger.info("Language detected via roman heuristic: %s", roman_guess)
        return roman_guess
    except Exception as exc:
        logger.warning("Language detection failed, defaulting to en: %s", exc)
        return "en"

