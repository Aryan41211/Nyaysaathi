"""Generate and persist category embeddings for semantic search using local models."""

from __future__ import annotations

import datetime as dt
import logging
from collections import defaultdict
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL
from legal_cases.db_connection import get_collection

logger = logging.getLogger(__name__)

_EMBED_COLL = "category_embeddings"
_CASES_COLL = "legal_cases"


def _build_category_documents() -> list[dict[str, str]]:
    """Aggregate dataset categories into multiple example phrases per category."""
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

    items: list[dict[str, Any]] = []
    for category, payload in grouped.items():
        examples: list[str] = []

        # Use several concrete user-problem descriptions as category examples.
        for description in payload["descriptions"][:20]:
            cleaned = str(description).strip()
            if cleaned:
                examples.append(cleaned)

        # Add lightweight synthetic examples derived from subcategories.
        for subcategory in payload["subcategories"][:12]:
            cleaned_sub = str(subcategory).strip()
            if cleaned_sub:
                examples.append(f"Issue about {cleaned_sub} under {category}")
                examples.append(f"Legal complaint related to {cleaned_sub}")

        # Add exactly five category-level phrases for broader semantic recall.
        first_sub = payload["subcategories"][0] if payload["subcategories"] else category
        second_sub = payload["subcategories"][1] if len(payload["subcategories"]) > 1 else first_sub
        examples.extend(
            [
                f"legal complaint related to {category}",
                f"need legal help for {category} issue",
                f"problem about {first_sub}",
                f"guidance needed for {second_sub}",
                f"{category} dispute requiring action",
            ]
        )

        # Keep deterministic order but deduplicate.
        deduped: list[str] = []
        seen: set[str] = set()
        for example in examples:
            key = example.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(example)

        if not deduped:
            deduped = [f"General legal issue in {category}"]

        items.append({"category": category, "examples": deduped})

    return items


def _embed_texts(texts: list[str]) -> list[list[float]]:
    model = SentenceTransformer(EMBEDDING_MODEL)
    vectors: list[list[float]] = []

    for idx in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[idx : idx + EMBEDDING_BATCH_SIZE]
        matrix = model.encode(batch, normalize_embeddings=True, convert_to_numpy=True)
        vectors.extend(np.asarray(matrix, dtype=np.float32).tolist())

    return vectors


def generate_and_store_embeddings() -> dict[str, Any]:
    """Compute category embeddings and store in MongoDB."""
    category_docs = _build_category_documents()
    if not category_docs:
        return {"status": "no_data", "count": 0}

    coll = get_collection(_EMBED_COLL)
    coll.create_index([("category", 1), ("model", 1)], unique=True)

    upserts = 0
    now = dt.datetime.utcnow()
    for item in category_docs:
        examples = [str(text).strip() for text in item.get("examples", []) if str(text).strip()]
        vectors = _embed_texts(examples)
        matrix = np.asarray(vectors, dtype=np.float32)
        centroid = matrix.mean(axis=0).tolist() if len(matrix) else []

        coll.update_one(
            {"category": item["category"], "model": EMBEDDING_MODEL},
            {
                "$set": {
                    "category": item["category"],
                    "examples": examples,
                    "embeddings": vectors,
                    # Keep centroid for backward compatibility with older readers.
                    "embedding": centroid,
                    "model": EMBEDDING_MODEL,
                    "updated_at": now,
                }
            },
            upsert=True,
        )
        upserts += 1

    logger.info("Generated and stored %d category embeddings", upserts)
    return {"status": "ok", "count": upserts, "model": EMBEDDING_MODEL}
