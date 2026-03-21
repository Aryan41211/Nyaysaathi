"""Admin analytics helpers for NyaySaathi query monitoring."""

from __future__ import annotations

from typing import Any
import logging

from legal_cases.db_connection import get_collection

from .query_logger import COLLECTION_NAME, get_recent_queries

logger = logging.getLogger(__name__)


def get_category_stats() -> dict[str, int]:
    """Return frequency counts of classified categories."""
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    try:
        rows = list(get_collection(COLLECTION_NAME).aggregate(pipeline))
        return {str(item.get("_id", "Unknown")): int(item.get("count", 0)) for item in rows}
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_category_stats fallback due to DB error: %s", exc)
        return {}


def get_admin_queries(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent query rows with fields needed by admin UI."""
    rows = get_recent_queries(limit=limit)
    slim: list[dict[str, Any]] = []
    for row in rows:
        slim.append(
            {
                "query": row.get("query_text", ""),
                "category": row.get("category", "Unknown"),
                "confidence": row.get("confidence", "Low"),
                "timestamp": row.get("timestamp"),
                "user_id": row.get("user_id", "anonymous"),
            }
        )
    return slim
