from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SearchResult:
    indices: np.ndarray
    scores: np.ndarray


class FaissCaseIndex:
    """FAISS-backed vector index with numpy fallback."""

    def __init__(self, dimension: int):
        self.dimension = dimension
        self._index = None
        self._vectors = None
        self._faiss_available = False

        try:
            import faiss  # type: ignore

            self._faiss = faiss
            self._faiss_available = True
        except Exception:
            self._faiss = None
            self._faiss_available = False

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        vectors = vectors.astype("float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        return vectors / norms

    def build(self, embeddings: np.ndarray) -> None:
        vectors = self._normalize(embeddings)
        self._vectors = vectors

        if self._faiss_available:
            index = self._faiss.IndexFlatIP(self.dimension)
            index.add(vectors)
            self._index = index

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> SearchResult:
        if self._vectors is None or len(self._vectors) == 0:
            return SearchResult(indices=np.array([], dtype=int), scores=np.array([], dtype=float))

        query = self._normalize(query_vector.reshape(1, -1))
        k = min(top_k, len(self._vectors))

        if self._faiss_available and self._index is not None:
            scores, indices = self._index.search(query, k)
            return SearchResult(indices=indices[0], scores=scores[0])

        # Fallback cosine search without FAISS.
        scores = np.dot(self._vectors, query[0])
        ranked_idx = np.argsort(scores)[::-1][:k]
        ranked_scores = scores[ranked_idx]
        return SearchResult(indices=ranked_idx, scores=ranked_scores)
