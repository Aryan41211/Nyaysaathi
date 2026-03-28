"""Query logging utilities for user history and audit analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import logging
from threading import Lock

from legal_cases.db_connection import get_collection

COLLECTION_NAME = "user_queries"
TRAINING_EVENTS_COLLECTION = "training_events"
TRAINING_FEEDBACK_COLLECTION = "training_feedback"
logger = logging.getLogger(__name__)
_INDEX_READY = False
_INDEX_LOCK = Lock()


def _ensure_indexes() -> None:
    global _INDEX_READY
    if _INDEX_READY:
        return

    with _INDEX_LOCK:
        if _INDEX_READY:
            return
        try:
            col = get_collection(COLLECTION_NAME)
            col.create_index("user_id")
            col.create_index("category")
            col.create_index("created_at")
            col.create_index([("user_id", 1), ("created_at", -1)])

            training_col = get_collection(TRAINING_EVENTS_COLLECTION)
            training_col.create_index("user_id")
            training_col.create_index("intent")
            training_col.create_index("decision")
            training_col.create_index("created_at")
            training_col.create_index([("query_normalized", 1), ("created_at", -1)])

            feedback_col = get_collection(TRAINING_FEEDBACK_COLLECTION)
            feedback_col.create_index("user_id")
            feedback_col.create_index("created_at")
            feedback_col.create_index("request_id")
            feedback_col.create_index("resolved")
            _INDEX_READY = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("index creation skipped due to DB error: %s", exc)


def log_query(user_id: str, query: str, category: str, confidence: str) -> None:
    """Store a user query event in MongoDB."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id or "anonymous"),
        "query_text": str(query or "").strip(),
        "category": str(category or "Unknown"),
        "confidence": str(confidence or "Low"),
        "timestamp": now,
        "created_at": now,
    }
    try:
        _ensure_indexes()
        get_collection(COLLECTION_NAME).insert_one(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("log_query skipped due to DB error: %s", exc)


def get_user_history(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch user query history ordered by newest first."""
    uid = str(user_id or "anonymous")
    try:
        _ensure_indexes()
        cursor = (
            get_collection(COLLECTION_NAME)
            .find({"user_id": uid}, {"_id": 0})
            .sort("created_at", -1)
            .limit(max(1, int(limit)))
        )
        return list(cursor)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_user_history fallback due to DB error: %s", exc)
        return []


def get_recent_queries(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Fetch recent global query log rows for admin dashboards."""
    try:
        _ensure_indexes()
        cursor = (
            get_collection(COLLECTION_NAME)
            .find({}, {"_id": 0})
            .sort("created_at", -1)
            .skip(max(0, int(offset)))
            .limit(max(1, int(limit)))
        )
        return list(cursor)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_recent_queries fallback due to DB error: %s", exc)
        return []


def log_training_event(
    *,
    user_id: str,
    query_raw: str,
    query_normalized: str,
    language: str,
    intent: str,
    confidence: str,
    decision: str,
    system_response: str,
    workflow_steps: list[str],
    documents_required: list[str],
    request_id: str,
    source: str,
) -> None:
    """Store model training event row for continual quality improvements."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id or "anonymous"),
        "query_raw": str(query_raw or "").strip(),
        "query_normalized": str(query_normalized or query_raw or "").strip(),
        "language": str(language or "unknown").strip().lower(),
        "intent": str(intent or "General legal issue"),
        "confidence": str(confidence or "Low"),
        "decision": str(decision or "fallback"),
        "system_response": str(system_response or "").strip(),
        "workflow_steps": [str(step) for step in (workflow_steps or []) if str(step).strip()],
        "documents_required": [str(doc) for doc in (documents_required or []) if str(doc).strip()],
        "request_id": str(request_id or ""),
        "source": str(source or "search"),
        "timestamp": now,
        "created_at": now,
    }
    try:
        _ensure_indexes()
        get_collection(TRAINING_EVENTS_COLLECTION).insert_one(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("log_training_event skipped due to DB error: %s", exc)


def log_user_feedback(
    *,
    user_id: str,
    request_id: str,
    query_raw: str,
    system_response: str,
    correction_text: str,
    corrected_intent: str,
    corrected_language: str,
    is_helpful: bool | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Store user correction row used for intent updates and supervised tuning."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": str(user_id or "anonymous"),
        "request_id": str(request_id or "").strip(),
        "query_raw": str(query_raw or "").strip(),
        "system_response": str(system_response or "").strip(),
        "correction_text": str(correction_text or "").strip(),
        "corrected_intent": str(corrected_intent or "").strip(),
        "corrected_language": str(corrected_language or "").strip().lower(),
        "is_helpful": is_helpful,
        "resolved": bool(str(correction_text or "").strip()),
        "metadata": dict(metadata or {}),
        "timestamp": now,
        "created_at": now,
    }
    try:
        _ensure_indexes()
        get_collection(TRAINING_FEEDBACK_COLLECTION).insert_one(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("log_user_feedback skipped due to DB error: %s", exc)


def get_training_events(limit: int = 500, unresolved_only: bool = False) -> list[dict[str, Any]]:
    """Read training events for offline embedding/intent refresh jobs."""
    try:
        _ensure_indexes()
        query: dict[str, Any] = {}
        if unresolved_only:
            query["decision"] = "fallback"
        cursor = (
            get_collection(TRAINING_EVENTS_COLLECTION)
            .find(query, {"_id": 0})
            .sort("created_at", -1)
            .limit(max(1, int(limit)))
        )
        return list(cursor)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_training_events fallback due to DB error: %s", exc)
        return []


def get_feedback_samples(limit: int = 500, corrections_only: bool = True) -> list[dict[str, Any]]:
    """Read user feedback samples to drive synonym/intent improvements."""
    try:
        _ensure_indexes()
        query: dict[str, Any] = {}
        if corrections_only:
            query["resolved"] = True
        cursor = (
            get_collection(TRAINING_FEEDBACK_COLLECTION)
            .find(query, {"_id": 0})
            .sort("created_at", -1)
            .limit(max(1, int(limit)))
        )
        return list(cursor)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_feedback_samples fallback due to DB error: %s", exc)
        return []
