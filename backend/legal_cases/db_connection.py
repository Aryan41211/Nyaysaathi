"""
db_connection.py – MongoDB singleton for NyaySaathi
"""
import os
import time
import logging
from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)
_client = None
_last_failure_at = 0.0


def _mongo_retry_count() -> int:
    return max(1, int(os.getenv("MONGO_RETRY_COUNT", "3")))


def _mongo_retry_backoff_seconds() -> float:
    return max(0.1, float(os.getenv("MONGO_RETRY_BACKOFF_SECONDS", "0.25")))


def _mongo_failure_cooldown_seconds() -> float:
    return max(0.0, float(os.getenv("MONGO_FAILURE_COOLDOWN_SECONDS", "5")))


def _build_client() -> MongoClient:
    # Keep connection pool bounded for serverless safety.
    return MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "1000")),
        connectTimeoutMS=int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "1000")),
        socketTimeoutMS=int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "1000")),
        maxPoolSize=int(os.getenv("MONGO_MAX_POOL_SIZE", "20")),
        minPoolSize=int(os.getenv("MONGO_MIN_POOL_SIZE", "0")),
        retryWrites=True,
    )


def get_client():
    global _client
    global _last_failure_at

    if _client is None and _last_failure_at > 0.0:
        cooldown = _mongo_failure_cooldown_seconds()
        if time.time() - _last_failure_at < cooldown:
            raise ConnectionFailure("MongoDB temporarily unavailable (cooldown)")

    if _client is None:
        attempts = _mongo_retry_count()
        backoff = _mongo_retry_backoff_seconds()
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                candidate = _build_client()
                candidate.admin.command("ping")
                _client = candidate
                logger.info("MongoDB connected on attempt %s", attempt)
                break
            except ConnectionFailure as exc:
                last_error = exc
                logger.warning("MongoDB connect attempt %s/%s failed: %s", attempt, attempts, exc)
                if attempt < attempts:
                    time.sleep(backoff)
        if _client is None:
            logger.error("MongoDB connection failed after retries: %s", last_error)
            _last_failure_at = time.time()
            raise last_error
    return _client


def get_db():
    return get_client()[settings.MONGODB_DB]


def get_collection(name):
    return get_db()[name]


def create_indexes() -> None:
    """Create required Mongo indexes for users and query analytics."""
    db = get_db()
    db["users"].create_index("email", unique=True)
    db["user_queries"].create_index("user_id")
    db["user_queries"].create_index("category")
    db["user_queries"].create_index("created_at")


def mongo_health_status() -> str:
    """Return MongoDB health state string for readiness endpoints."""
    try:
        get_client().admin.command("ping")
        return "connected"
    except Exception:  # noqa: BLE001
        return "disconnected"
