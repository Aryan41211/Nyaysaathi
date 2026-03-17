from __future__ import annotations

import re

from ai_engine.hinglish_normalizer import HinglishNormalizer


class Preprocessor:
    _phone_re = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")
    _aadhaar_re = re.compile(r"(?<!\d)\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)")
    _space_re = re.compile(r"\s+")

    _hinglish_map = {
        "padosi": "neighbour",
        "tankhwa": "salary",
        "paisa": "money",
        "thana": "police station",
        "kirayedar": "tenant",
        "makaan malik": "landlord",
    }

    def __init__(self) -> None:
        self.hinglish_normalizer = HinglishNormalizer()

    def process(self, text: str) -> str:
        value = str(text or "").strip()
        value = self.hinglish_normalizer.normalize(value)
        value = self._space_re.sub(" ", value)

        lower = value.lower()
        for source, target in self._hinglish_map.items():
            lower = re.sub(rf"\b{re.escape(source)}\b", target, lower)

        lower = self._phone_re.sub("[PHONE_MASKED]", lower)
        lower = self._aadhaar_re.sub("[AADHAAR_MASKED]", lower)
        return lower[:2000]