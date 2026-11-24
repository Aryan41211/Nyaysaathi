"""Cross-encoder reranker for NyaySaathi retrieval.

Wraps sentence-transformers CrossEncoder to re-rank top-k retrieval
candidates. The cross-encoder computes a more accurate relevance score
than bi-encoder (MiniLM) by attending to query and document jointly.

Usage:
    reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    scores = reranker.rank(query, docs, top_n=5)
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np


class CrossEncoderReranker:
    """Cross-encoder based re-ranker for retrieval candidates.

    Loads a cross-encoder model (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
    and scores query-document pairs jointly for more accurate relevance ranking.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_length: int = 512,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.max_length = max_length
        self.device = device
        self._model = None
        self._model_error: Optional[str] = None

    def _load_model(self) -> bool:
        """Lazily load the cross-encoder model. Returns True on success."""
        if self._model is not None:
            return True
        if self._model_error is not None:
            return False
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.model_name, max_length=self.max_length, device=self.device
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self._model_error = str(exc)
            return False

    def rank(
        self,
        query: str,
        docs: List[str],
        top_n: int | None = None,
    ) -> List[tuple[int, float]]:
        """Re-rank documents for a query.

        Args:
            query: The user query string.
            docs: List of document text strings to re-rank.
            top_n: Number of top results to return. If None, returns all.

        Returns:
            List of (doc_index, score) tuples sorted by score descending.
            Returns empty list if model unavailable.
        """
        if not docs:
            return []
        if not self._load_model():
            return []

        pairs = [(query, doc) for doc in docs]
        scores = self._model.predict(pairs, show_progress_bar=False)
        scores = np.asarray(scores, dtype=float)

        ranked = sorted(
            enumerate(scores.tolist()), key=lambda x: x[1], reverse=True
        )
        if top_n is not None:
            ranked = ranked[:top_n]
        return [(int(idx), float(score)) for idx, score in ranked]

    @property
    def model_error(self) -> Optional[str]:
        return self._model_error

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
