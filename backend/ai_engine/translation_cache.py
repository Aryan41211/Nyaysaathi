"""Persistent translation cache backed by MongoDB."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from legal_cases.db_connection import get_collection

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "workflow_translations"


def _collection():
    col = get_collection(_COLLECTION_NAME)
    try:
        col.create_index([("category", 1), ("language", 1)], unique=True)
    except Exception as exc:
        logger.debug("Translation cache index creation skipped/failed: %s", exc)
    return col


def get_cached_translation(category: str, language: str) -> list[str] | None:
    """Fetch cached translated workflow steps by category+language."""
    try:
        doc = _collection().find_one(
            {
                "category": (category or "").strip(),
                "language": (language or "").strip().lower(),
            },
            {"_id": 0, "translated_text": 1},
        )
        if not doc:
            return None

        translated = doc.get("translated_text", [])
        if isinstance(translated, list) and translated:
            return [str(step) for step in translated]
        return None
    except Exception as exc:
        logger.warning("Persistent translation cache read failed: %s", exc)
        return None


def store_translation(category: str, language: str, text: list[str]) -> bool:
    """Store translated workflow in persistent cache."""
    try:
        if not text:
            return False

        now = dt.datetime.utcnow()
        _collection().update_one(
            {
                "category": (category or "").strip(),
                "language": (language or "").strip().lower(),
            },
            {
                "$set": {
                    "translated_text": [str(step) for step in text],
                    "created_at": now,
                }
            },
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.warning("Persistent translation cache write failed: %s", exc)
        return False


def get_cache_entry_count() -> int:
    """Return total count of persistent cached translations."""
    try:
        return int(_collection().count_documents({}))
    except Exception as exc:
        logger.warning("Persistent translation cache count failed: %s", exc)
        return 0

