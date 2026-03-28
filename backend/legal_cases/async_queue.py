"""Async task adapter for scalable search processing.

Supports two modes:
1) Celery mode when CELERY_BROKER_URL is configured and Celery is installed.
2) Local thread-pool fallback for single-node deployments.
"""

from __future__ import annotations

import os
import threading
import importlib
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from utils.logger import get_logger

from . import services

logger = get_logger(__name__)

_USE_CELERY = bool(str(os.getenv("CELERY_BROKER_URL", "")).strip())
_ASYNC_WORKERS = max(2, int(os.getenv("ASYNC_LOCAL_WORKERS", "8")))

_EXECUTOR = ThreadPoolExecutor(max_workers=_ASYNC_WORKERS, thread_name_prefix="nyay-async")
_FUTURES: dict[str, Future] = {}
_FUTURES_LOCK = threading.Lock()


if _USE_CELERY:
    try:
        celery_mod = importlib.import_module("celery")
        Celery = getattr(celery_mod, "Celery")

        celery_app = Celery(
            "nyaysaathi",
            broker=os.getenv("CELERY_BROKER_URL"),
            backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("CELERY_BROKER_URL")),
        )
        celery_app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            task_acks_late=True,
            worker_prefetch_multiplier=1,
        )

        @celery_app.task(name="legal_cases.search_task")
        def search_task(query: str, top_k: int = 5) -> dict[str, Any]:
            results, nlp_meta = services.search_cases(query, top_k=top_k)
            pipeline = services.build_standard_response(query=query, results=results, nlp_meta=nlp_meta)
            return {
                "query": query,
                "results": results,
                "nlp": nlp_meta,
                "pipeline": pipeline,
            }

        _CELERY_READY = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Celery unavailable, using local async executor: %s", exc)
        _CELERY_READY = False
else:
    _CELERY_READY = False


def _local_search_task(query: str, top_k: int) -> dict[str, Any]:
    results, nlp_meta = services.search_cases(query, top_k=top_k)
    pipeline = services.build_standard_response(query=query, results=results, nlp_meta=nlp_meta)
    return {
        "query": query,
        "results": results,
        "nlp": nlp_meta,
        "pipeline": pipeline,
    }


def enqueue_search(query: str, top_k: int = 5) -> dict[str, Any]:
    if _CELERY_READY:
        task = search_task.delay(query=query, top_k=top_k)
        return {"task_id": task.id, "provider": "celery", "status": "queued"}

    task_id = str(uuid4())
    future = _EXECUTOR.submit(_local_search_task, query, top_k)
    with _FUTURES_LOCK:
        _FUTURES[task_id] = future
    return {"task_id": task_id, "provider": "local", "status": "queued"}


def get_search_task(task_id: str) -> dict[str, Any]:
    if _CELERY_READY:
        state = search_task.AsyncResult(task_id)
        if not state.ready():
            return {"task_id": task_id, "status": state.status.lower(), "ready": False}
        if state.failed():
            return {
                "task_id": task_id,
                "status": "failed",
                "ready": True,
                "error": str(state.result),
            }
        return {
            "task_id": task_id,
            "status": "completed",
            "ready": True,
            "result": state.result,
        }

    with _FUTURES_LOCK:
        future = _FUTURES.get(task_id)

    if not future:
        return {"task_id": task_id, "status": "not_found", "ready": True}

    if not future.done():
        return {"task_id": task_id, "status": "running", "ready": False}

    try:
        result = future.result()
        return {"task_id": task_id, "status": "completed", "ready": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        return {"task_id": task_id, "status": "failed", "ready": True, "error": str(exc)}
    finally:
        with _FUTURES_LOCK:
            _FUTURES.pop(task_id, None)
