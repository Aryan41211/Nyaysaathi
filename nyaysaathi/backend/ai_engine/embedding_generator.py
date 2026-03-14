"""Generate and persist category embeddings for semantic search."""
from __future__ import annotations

import datetime as dt
import logging
import os
from collections import defaultdict
from typing import Any

from config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL
from legal_cases.db_connection import get_collection
from openai import OpenAI

logger = logging.getLogger(__name__)

_EMBED_COLL = "category_embeddings"
_CASES_COLL = "legal_cases"


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embedding generation")
    return OpenAI(api_key=api_key)


def _build_category_documents() -> list[dict[str, str]]:
    """Aggregate dataset categories into embedding text blocks."""
    col = get_collection(_CASES_COLL)
    docs = list(col.find({}, {"_id": 0, "category": 1, "subcategory": 1, "problem_description": 1}))

    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"subcategories": [], "descriptions": []})
    for doc in docs:
        category = str(doc.get("category") or "General").strip()
        subcategory = str(doc.get("subcategory") or "").strip()
        description = str(doc.get("problem_description") or "").strip()
        if subcategory:
            grouped[category]["subcategories"].append(subcategory)
        if description:
            grouped[category]["descriptions"].append(description)

    items: list[dict[str, str]] = []
    for category, payload in grouped.items():
        sub_text = "; ".join(payload["subcategories"][:25])
        desc_text = " ".join(payload["descriptions"][:8])
        text = f"Category: {category}. Subcategories: {sub_text}. Typical problems: {desc_text}".strip()
        items.append({"category": category, "text": text})

    return items


def _embed_texts(texts: list[str]) -> list[list[float]]:
    client = _client()
    vectors: list[list[float]] = []

    for idx in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[idx : idx + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend([list(item.embedding) for item in response.data])

    return vectors


def generate_and_store_embeddings() -> dict[str, Any]:
    """Compute category embeddings and store in MongoDB."""
    category_docs = _build_category_documents()
    if not category_docs:
        return {"status": "no_data", "count": 0}

    vectors = _embed_texts([item["text"] for item in category_docs])
    coll = get_collection(_EMBED_COLL)
    coll.create_index([("category", 1), ("model", 1)], unique=True)

    upserts = 0
    now = dt.datetime.utcnow()
    for item, vector in zip(category_docs, vectors):
        coll.update_one(
            {"category": item["category"], "model": EMBEDDING_MODEL},
            {
                "$set": {
                    "category": item["category"],
                    "text": item["text"],
                    "embedding": vector,
                    "model": EMBEDDING_MODEL,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        upserts += 1

    logger.info("Generated and stored %d category embeddings", upserts)
    return {"status": "ok", "count": upserts, "model": EMBEDDING_MODEL}
