from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from .config import EMBEDDING_CACHE_PATH, MODEL_NAME
from .data_loader import load_merged_cases


@dataclass
class RetrievalHit:
    case: Dict
    semantic_score: float


class SemanticRetriever:
    """Semantic retriever with lazy model loading and embedding cache."""

    def __init__(self) -> None:
        self._cases: List[Dict] = []
        self._embeddings: Optional[np.ndarray] = None
        self._model = None
        self._model_error = None
        self._ready = False

    @property
    def model_error(self):
        return self._model_error

    def _get_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(MODEL_NAME)
            return self._model
        except Exception as exc:
            self._model_error = str(exc)
            return None

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        vectors = vectors.astype("float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        return vectors / norms

    def _load_embeddings_cache(self) -> Optional[np.ndarray]:
        if not EMBEDDING_CACHE_PATH.exists():
            return None

        try:
            data = np.load(EMBEDDING_CACHE_PATH, allow_pickle=False)
            vectors = data["embeddings"]
            count = int(data["count"])
            if count != len(self._cases):
                return None
            return vectors.astype("float32")
        except Exception:
            return None

    def _save_embeddings_cache(self, embeddings: np.ndarray) -> None:
        try:
            np.savez_compressed(
                EMBEDDING_CACHE_PATH,
                embeddings=embeddings,
                count=np.array([len(self._cases)], dtype=np.int32),
            )
        except Exception:
            # Cache write failure should never break runtime.
            return

    def ensure_ready(self) -> None:
        if self._ready:
            return

        self._cases = load_merged_cases()
        if not self._cases:
            self._ready = True
            return

        model = self._get_model()
        if model is None:
            self._ready = True
            return

        cached = self._load_embeddings_cache()
        if cached is not None:
            self._embeddings = self._normalize(cached)
            self._ready = True
            return

        corpus = [case["searchable_text"] for case in self._cases]
        vectors = model.encode(corpus, convert_to_numpy=True, normalize_embeddings=True)
        vectors = self._normalize(np.asarray(vectors, dtype="float32"))
        self._embeddings = vectors
        self._save_embeddings_cache(vectors)
        self._ready = True

    def _keyword_fallback(self, query_text: str, top_k: int) -> List[RetrievalHit]:
        q_terms = [x for x in query_text.split() if x]
        scored = []

        for case in self._cases:
            text = case.get("searchable_text", "").lower()
            overlap = sum(1 for term in q_terms if term in text)
            score = overlap / max(1, len(q_terms))
            scored.append(RetrievalHit(case=case, semantic_score=float(min(1.0, score))))

        scored.sort(key=lambda x: x.semantic_score, reverse=True)
        return scored[:top_k]

    def search(self, query_text: str, top_k: int = 5) -> List[RetrievalHit]:
        self.ensure_ready()

        if not query_text.strip() or not self._cases:
            return []

        model = self._get_model()
        if model is None or self._embeddings is None:
            return self._keyword_fallback(query_text.lower(), top_k=top_k)

        query_vec = model.encode([query_text], convert_to_numpy=True, normalize_embeddings=True)
        query_vec = self._normalize(np.asarray(query_vec, dtype="float32"))[0]

        sims = np.dot(self._embeddings, query_vec)
        k = min(top_k, len(self._cases))
        ranked_idx = np.argsort(sims)[::-1][:k]

        return [
            RetrievalHit(case=self._cases[i], semantic_score=float(max(0.0, min(1.0, sims[i]))))
            for i in ranked_idx
        ]


_RETRIEVER = SemanticRetriever()


def get_retriever() -> SemanticRetriever:
    return _RETRIEVER
