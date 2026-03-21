"""Query logging utilities for user history and audit analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import logging

from legal_cases.db_connection import get_collection

COLLECTION_NAME = "user_queries"
logger = logging.getLogger(__name__)


def log_query(user_id: str, query: str, category: str, confidence: str) -> None:
    """Store a user query event in MongoDB."""
    payload = {
        "user_id": str(user_id or "anonymous"),
        "query_text": str(query or "").strip(),
        "category": str(category or "Unknown"),
        "confidence": str(confidence or "Low"),
        "timestamp": datetime.now(timezone.utc),
    }
    try:
        get_collection(COLLECTION_NAME).insert_one(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("log_query skipped due to DB error: %s", exc)


def get_user_history(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch user query history ordered by newest first."""
    uid = str(user_id or "anonymous")
    try:
        cursor = (
            get_collection(COLLECTION_NAME)
            .find({"user_id": uid}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(max(1, int(limit)))
        )
        return list(cursor)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_user_history fallback due to DB error: %s", exc)
        return []


def get_recent_queries(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch recent global query log rows for admin dashboards."""
    try:
        cursor = (
            get_collection(COLLECTION_NAME)
            .find({}, {"_id": 0})
            .sort("timestamp", -1)
            .limit(max(1, int(limit)))
        )
        return list(cursor)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_recent_queries fallback due to DB error: %s", exc)
        return []
