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
    "paisa",
    "nahi",
    "karaycha",
)

# Hindi signal terms commonly seen in Roman script.
_HINDI_ROMAN_HINTS: Final[tuple[str, ...]] = (
    "mera",
    "meri",
    "nahi",
    "kya",
    "mila",
    "paisa",
    "police",
    "shikayat",
    "complaint",
    "kaise",
)

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def _detect_devanagari_variant(text: str) -> str:
    """Heuristic split between Hindi/Marathi when input is in Devanagari."""
    lowered = text.lower()
    marathi_signals = ("à¤†à¤¹à¥‡", "à¤à¤¾à¤²à¥€", "à¤®à¤¾à¤", "à¤¨à¤¾à¤¹à¥€", "à¤˜à¤°à¤¾à¤¤")
    hindi_signals = ("à¤¹à¥ˆ", "à¤¨à¤¹à¥€à¤‚", "à¤®à¥‡à¤°à¤¾", "à¤®à¥‡à¤°à¥€", "à¤•à¥ƒà¤ªà¤¯à¤¾")

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

    if marathi_hits > hindi_hits and marathi_hits >= 1:
        return "mr"
    if hindi_hits >= 1:
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
                        "Language confidence low (%.3f), fallback=en",
                        top_prob,
                    )
                    return "en"

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

