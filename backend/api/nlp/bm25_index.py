"""BM25 sparse retrieval index for NyaySaathi legal cases.

Uses the ``rank_bm25`` library (Okapi BM25) over the same ``searchable_text``
corpus used by the MiniLM dense index. Provides exact keyword matching that
complements dense semantic retrieval in a hybrid pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from rank_bm25 import BM25Okapi


class BM25Index:
    """BM25 Okapi index over a list of document dictionaries."""

    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self._tokenized_corpus: List[List[str]] = []
        self._bm25: BM25Okapi | None = None
        self._build(documents)

    def _build(self, documents: List[Dict[str, Any]]) -> None:
        # Build a searchable text from available fields; CASES from
        # api.data_loader does not have a precomputed searchable_text field.
        self.documents = documents
        self._tokenized_corpus: List[List[str]] = []
        self._valid_indices: List[int] = []
        for idx, doc in enumerate(documents):
            text = " ".join(
                str(doc.get(k, "")) for k in (
                    "category", "subcategory", "problem_description",
                    "descriptions", "workflow_steps", "required_documents",
                ) if doc.get(k)
            )
            if isinstance(doc.get("descriptions"), list):
                text += " " + " ".join(doc["descriptions"])
            if isinstance(doc.get("workflow_steps"), list):
                text += " " + " ".join(doc["workflow_steps"])
            tokens = self._tokenize(text)
            if tokens:
                self._tokenized_corpus.append(tokens)
                self._valid_indices.append(idx)
        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25 = None

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Lightweight tokenizer: lowercase, split on non-alphanumeric."""
        import re

        return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t]

    def refresh(self, documents: List[Dict[str, Any]]) -> None:
        """Rebuild the index from a new document list (incremental updates)."""
        self.documents = documents
        self._build(documents)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top-k documents ranked by BM25 score.

        Each result includes the original document plus a ``bm25_score`` field.
        """
        if self._bm25 is None or not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        # rank_bm25 returns scores aligned with corpus order.
        ranked_idx = np.argsort(scores)[::-1][:top_k]

        results: List[Dict[str, Any]] = []
        for corpus_idx in ranked_idx:
            if scores[corpus_idx] <= 0:
                continue
            orig_idx = self._valid_indices[int(corpus_idx)]
            doc = dict(self.documents[orig_idx])
            doc["bm25_score"] = float(scores[int(corpus_idx)])
            results.append(doc)

        return results

    def __len__(self) -> int:
        return len(self.documents)
