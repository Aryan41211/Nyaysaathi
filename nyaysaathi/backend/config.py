"""Central runtime configuration for NyaySaathi backend reliability layers."""

from __future__ import annotations

import os

SUPPORTED_LANGUAGES = ["en", "hi", "mr"]
LANG_DETECT_MIN_CONFIDENCE = float(os.getenv("LANG_DETECT_MIN_CONFIDENCE", "0.70"))

TRANSLATION_TIMEOUT = float(os.getenv("TRANSLATION_TIMEOUT", "10"))
TRANSLATION_RETRIES = int(os.getenv("TRANSLATION_RETRIES", "2"))
TRANSLATION_CB_THRESHOLD = int(os.getenv("TRANSLATION_CB_THRESHOLD", "4"))
TRANSLATION_CB_COOLDOWN = float(os.getenv("TRANSLATION_CB_COOLDOWN", "45"))

ROMAN_NORMALIZER_TIMEOUT = float(os.getenv("ROMAN_NORMALIZER_TIMEOUT", "8"))
ROMAN_NORMALIZER_RETRIES = int(os.getenv("ROMAN_NORMALIZER_RETRIES", "1"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
SEMANTIC_MATCH_THRESHOLD = float(os.getenv("SEMANTIC_MATCH_THRESHOLD", "0.55"))
EMBEDDING_CACHE_TTL_SECONDS = int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", "900"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
