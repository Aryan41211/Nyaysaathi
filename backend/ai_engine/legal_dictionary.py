"""Offline legal terminology mapping for translation consistency."""
from __future__ import annotations

import re
from typing import Final

LEGAL_TERMS: Final[dict[str, dict[str, str]]] = {
    "FIR": {
        "mr": "à¤ªà¥à¤°à¤¥à¤® à¤®à¤¾à¤¹à¤¿à¤¤à¥€ à¤…à¤¹à¤µà¤¾à¤²",
        "hi": "à¤ªà¥à¤°à¤¥à¤® à¤¸à¥‚à¤šà¤¨à¤¾ à¤°à¤¿à¤ªà¥‹à¤°à¥à¤Ÿ",
    },
    "bail": {
        "mr": "à¤œà¤¾à¤®à¥€à¤¨",
        "hi": "à¤œà¤®à¤¾à¤¨à¤¤",
    },
    "complaint": {
        "mr": "à¤¤à¤•à¥à¤°à¤¾à¤°",
        "hi": "à¤¶à¤¿à¤•à¤¾à¤¯à¤¤",
    },
}


def apply_legal_dictionary(text: str, language: str) -> str:
    """Apply deterministic legal term substitutions before translation."""
    lang = (language or "").lower()
    if lang not in {"hi", "mr"}:
        return text

    updated = text or ""
    for english_term, localized in LEGAL_TERMS.items():
        target = localized.get(lang)
        if not target:
            continue

        pattern = re.compile(rf"\b{re.escape(english_term)}\b", re.IGNORECASE)
        updated = pattern.sub(target, updated)

    return updated

