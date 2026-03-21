"""Vectorized similarity engine for local semantic classification."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .embedding_engine import EmbeddingStore


def find_best_match(user_embedding: np.ndarray, store: EmbeddingStore) -> dict[str, Any]:
    """Return best sentence-level semantic match across all category phrases."""
    if store.dataset_embeddings.size == 0 or not store.dataset_texts:
        return {
            "category": "Unknown",
            "matched_text": "",
            "similarity": 0.0,
            "index": -1,
        }

    user_vector = np.asarray(user_embedding, dtype=np.float32).reshape(1, -1)
    scores = cosine_similarity(user_vector, store.dataset_embeddings)[0]
    best_index = int(np.argmax(scores))
    best_similarity = float(scores[best_index])

    return {
        "category": store.dataset_categories[best_index],
        "matched_text": store.dataset_texts[best_index],
        "similarity": round(best_similarity, 4),
        "index": best_index,
    }
