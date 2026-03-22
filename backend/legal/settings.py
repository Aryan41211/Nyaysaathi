"""Legal AI module configuration loaded from environment variables."""

from __future__ import annotations

import os

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
FALLBACK_SIMILARITY_THRESHOLD = float(os.getenv("FALLBACK_SIMILARITY_THRESHOLD", "0.50"))
HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.80"))
MEDIUM_CONFIDENCE_THRESHOLD = float(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "0.65"))
