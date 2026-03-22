"""Local embedding based semantic category search with keyword backup."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import numpy as np

from config import EMBEDDING_CACHE_TTL_SECONDS, EMBEDDING_MODEL, SEMANTIC_MATCH_THRESHOLD
from legal_cases.db_connection import get_collection
from utils.ai_runtime import load_sentence_transformer

logger = logging.getLogger(__name__)

_EMBED_COLL = "category_embeddings"
_CACHE_LOCK = threading.Lock()
_EMBED_CACHE: dict[str, Any] = {"expires": 0.0, "rows": []}
_MODEL: Any | None = None
_MODEL_LOCK = threading.Lock()


def _model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            _MODEL = load_sentence_transformer(EMBEDDING_MODEL)
            logger.info("Loaded semantic model lazily: %s", EMBEDDING_MODEL)
    return _MODEL


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _load_embeddings() -> list[dict[str, Any]]:
    now = time.time()
    with _CACHE_LOCK:
        if _EMBED_CACHE["rows"] and _EMBED_CACHE["expires"] > now:
            return list(_EMBED_CACHE["rows"])

    rows = list(get_collection(_EMBED_COLL).find({"model": EMBEDDING_MODEL}, {"_id": 0}))

    with _CACHE_LOCK:
        _EMBED_CACHE["rows"] = rows
        _EMBED_CACHE["expires"] = now + EMBEDDING_CACHE_TTL_SECONDS

    return rows


def _embed_query(query: str) -> np.ndarray:
    matrix = _model().encode([query], normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(matrix[0], dtype=np.float32)


def keyword_backup_category(query: str, categories: list[str]) -> str:
    """Simple keyword backup category scoring for hybrid behavior."""
    q_tokens = set(str(query).lower().split())
    best = ""
    best_score = 0
    for cat in categories:
        tokens = set(cat.lower().split())
        score = len(q_tokens & tokens)
        if score > best_score:
            best = cat
            best_score = score
    return best if best_score > 0 else ""


def find_best_category(user_input: str) -> dict[str, Any]:
    """Semantic-first category matcher using local embeddings."""
    query = (user_input or "").strip()
    if not query:
        return {"category": "", "similarity": 0.0, "status": "unknown", "source": "none"}

    rows = _load_embeddings()
    if not rows:
        return {"category": "", "similarity": 0.0, "status": "unknown", "source": "none"}

    categories = [str(item.get("category", "")) for item in rows if str(item.get("category", ""))]

    try:
        query_vec = _embed_query(query)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Semantic embedding generation failed: %s", exc)
        kb = keyword_backup_category(query, categories)
        return {
            "category": kb,
            "similarity": 0.0,
            "status": "ok" if kb else "unknown",
            "source": "keyword_backup" if kb else "none",
        }

    best_category = ""
    best_score = -1.0
    for row in rows:
        embeddings = row.get("embeddings")
        emb = row.get("embedding")
        category = str(row.get("category", "")).strip()
        if not category:
            continue

        category_score = -1.0

        # Preferred path: multiple example embeddings per category.
        if isinstance(embeddings, list) and embeddings:
            for candidate in embeddings:
                if not candidate:
                    continue
                score = _cosine_similarity(query_vec, np.array(candidate, dtype=np.float32))
                if score > category_score:
                    category_score = score

        # Backward-compatible path: single centroid embedding.
        if category_score < 0 and emb:
            category_score = _cosine_similarity(query_vec, np.array(emb, dtype=np.float32))

        if category_score > best_score:
            best_score = category_score
            best_category = category

    if best_score >= SEMANTIC_MATCH_THRESHOLD and best_category:
        return {
            "category": best_category,
            "similarity": round(float(best_score), 4),
            "status": "ok",
            "source": "semantic",
        }

    kb = keyword_backup_category(query, categories)
    return {
        "category": kb,
        "similarity": round(float(max(best_score, 0.0)), 4),
        "status": "ok" if kb else "unknown",
        "source": "keyword_backup" if kb else "none",
    }
