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
    return max(0.1, float(os.getenv("MONGO_RETRY_BACKOFF_SECONDS", "1.0")))


def _mongo_failure_cooldown_seconds() -> float:
    return max(0.0, float(os.getenv("MONGO_FAILURE_COOLDOWN_SECONDS", "5")))


def _build_client(timeout_ms: int | None = None) -> MongoClient:
    effective_timeout_ms = timeout_ms if timeout_ms is not None else int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "30000"))
    effective_server_timeout_ms = timeout_ms if timeout_ms is not None else int(
        os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "30000")
    )
    effective_socket_timeout_ms = timeout_ms if timeout_ms is not None else int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "30000"))

    # Keep connection pool bounded for serverless safety.
    return MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=effective_server_timeout_ms,
        connectTimeoutMS=effective_timeout_ms,
        socketTimeoutMS=effective_socket_timeout_ms,
        maxPoolSize=int(os.getenv("MONGO_MAX_POOL_SIZE", "20")),
        minPoolSize=int(os.getenv("MONGO_MIN_POOL_SIZE", "0")),
        retryWrites=True,
    )


def get_client(raise_on_error: bool = True, quick: bool = False):
    global _client
    global _last_failure_at

    if _client is None and _last_failure_at > 0.0:
        cooldown = _mongo_failure_cooldown_seconds()
        if time.time() - _last_failure_at < cooldown:
            if raise_on_error:
                raise ConnectionFailure("MongoDB temporarily unavailable (cooldown)")
            return None

    if _client is None:
        attempts = 1 if quick else _mongo_retry_count()
        backoff = _mongo_retry_backoff_seconds()
        last_error = None
        timeout_override = int(os.getenv("MONGO_QUICK_TIMEOUT_MS", "2000")) if quick else None
        for attempt in range(1, attempts + 1):
            try:
                candidate = _build_client(timeout_ms=timeout_override)
                candidate.admin.command("ping")
                _client = candidate
                logger.info("MongoDB connected on attempt %s", attempt)
                break
            except Exception as exc:
                last_error = exc
                logger.warning("MongoDB connect attempt %s/%s failed: %s", attempt, attempts, exc)
                if attempt < attempts:
                    time.sleep(backoff)
        if _client is None:
            logger.error("MongoDB connection failed after retries: %s", last_error)
            _last_failure_at = time.time()
            if raise_on_error:
                raise ConnectionFailure(str(last_error)) from last_error
            return None
    return _client


def get_db():
    client = get_client(raise_on_error=True)
    return client[settings.MONGODB_DB]


def get_collection(name):
    return get_db()[name]


def create_indexes() -> None:
    """Create required Mongo indexes for users and query analytics."""
    try:
        db = get_db()
        db["users"].create_index("email", unique=True)
        db["user_queries"].create_index("user_id")
        db["user_queries"].create_index("category")
        db["user_queries"].create_index("created_at")
        logger.info("Mongo indexes ensured")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skipping Mongo index creation for now: %s", exc)


def mongo_health_status() -> str:
    """Return MongoDB health state string for readiness endpoints."""
    try:
        client = get_client(raise_on_error=False)
        if client is None:
            return "disconnected"
        client.admin.command("ping")
        return "connected"
    except Exception:  # noqa: BLE001
        return "disconnected"
