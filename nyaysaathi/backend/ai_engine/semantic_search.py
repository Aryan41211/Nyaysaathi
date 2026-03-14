"""OpenAI embedding based semantic category search with hybrid fallback."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import threading
import time
from typing import Any

import numpy as np

from config import EMBEDDING_CACHE_TTL_SECONDS, EMBEDDING_MODEL, SEMANTIC_MATCH_THRESHOLD
from legal_cases.db_connection import get_collection
from openai import OpenAI

logger = logging.getLogger(__name__)

_EMBED_COLL = "category_embeddings"
_CACHE_LOCK = threading.Lock()
_EMBED_CACHE: dict[str, Any] = {"expires": 0.0, "rows": []}
_OPENAI_DISABLED_UNTIL = 0.0


def _openai_temporarily_disabled() -> bool:
    return time.time() < _OPENAI_DISABLED_UNTIL


def _mark_quota_exhausted(cooldown_seconds: float = 900.0) -> None:
    global _OPENAI_DISABLED_UNTIL
    _OPENAI_DISABLED_UNTIL = time.time() + max(60.0, cooldown_seconds)


def _openai_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "")) and not _openai_temporarily_disabled()


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=api_key)


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
    response = _client().embeddings.create(model=EMBEDDING_MODEL, input=[query])
    return np.array(response.data[0].embedding, dtype=np.float32)


def _ai_fallback_category(query: str, category_options: list[str]) -> str:
    """LLM classification fallback when similarity is unclear."""
    if not _openai_available() or not category_options:
        return ""

    system_prompt = (
        "You classify legal user issues into one category from provided options. "
        "Return strict JSON with key category only."
    )
    user_prompt = json.dumps({"query": query, "categories": category_options}, ensure_ascii=True)

    try:
        response = _client().chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.1,
            response_format={"type": "json_object"},
            timeout=8,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        payload = json.loads((response.choices[0].message.content or "").strip().replace("```json", "").replace("```", ""))
        category = str(payload.get("category", "")).strip()
        return category if category in category_options else ""
    except Exception as exc:
        logger.warning("AI fallback classification failed: %s", exc)
        return ""


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
    """
    Semantic-first category matcher using OpenAI embeddings.

    Returns:
      {
        category: str,
        similarity: float,
        status: "ok"|"unknown",
        source: "semantic"|"ai_fallback"|"keyword_backup"|"none"
      }
    """
    query = (user_input or "").strip()
    if not query:
        return {"category": "", "similarity": 0.0, "status": "unknown", "source": "none"}

    rows = _load_embeddings()
    if not rows:
        return {"category": "", "similarity": 0.0, "status": "unknown", "source": "none"}

    categories = [str(item.get("category", "")) for item in rows if str(item.get("category", ""))]

    if not _openai_available():
        kb = keyword_backup_category(query, categories)
        return {
            "category": kb,
            "similarity": 0.0,
            "status": "ok" if kb else "unknown",
            "source": "keyword_backup" if kb else "none",
        }

    try:
        query_vec = _embed_query(query)
    except Exception as exc:
        lowered = str(exc).lower()
        if (
            "insufficient_quota" in lowered
            or "insufficient quota" in lowered
            or "error code: 429" in lowered
        ):
            _mark_quota_exhausted()
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
        emb = row.get("embedding")
        category = str(row.get("category", "")).strip()
        if not emb or not category:
            continue
        score = _cosine_similarity(query_vec, np.array(emb, dtype=np.float32))
        if score > best_score:
            best_score = score
            best_category = category

    if best_score >= SEMANTIC_MATCH_THRESHOLD and best_category:
        return {
            "category": best_category,
            "similarity": round(float(best_score), 4),
            "status": "ok",
            "source": "semantic",
        }

    # AI fallback for unclear similarity.
    ai_cat = _ai_fallback_category(query, categories)
    if ai_cat:
        return {
            "category": ai_cat,
            "similarity": round(float(max(best_score, 0.0)), 4),
            "status": "ok",
            "source": "ai_fallback",
        }

    kb = keyword_backup_category(query, categories)
    return {
        "category": kb,
        "similarity": round(float(max(best_score, 0.0)), 4),
        "status": "ok" if kb else "unknown",
        "source": "keyword_backup" if kb else "none",
    }
