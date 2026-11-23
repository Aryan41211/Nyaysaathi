"""Hybrid retrieval for NyaySaathi.

Combines TF-IDF lexical, BM25 sparse, and MiniLM dense retrieval using
Reciprocal Rank Fusion (RRF). RRF is parameter-free and robust: a document
that ranks highly in any single system surfaces in the fused results.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

import numpy as np

from api.nlp.bm25_index import BM25Index
from api.nlp.faiss_index import FaissCaseIndex, SearchResult
from api.nlp.semantic_engine import SemanticSearchEngine
from api.search_engine import simple_search


def _rrf_rank(
    ranked_lists: List[List[Any]], k: int = 60
) -> List[Any]:
    """Reciprocal Rank Fusion over multiple ranked result lists.

    Each list is a sequence of document dicts (matched by ``id``). Returns the
    fused ranking with an ``rrf_score`` field on each document.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Any] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, start=1):
            doc_id = str(doc.get("id", rank))
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            doc_map[doc_id] = doc

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results: List[Any] = []
    for doc_id, score in fused:
        doc = dict(doc_map[doc_id])
        doc["rrf_score"] = float(score)
        results.append(doc)

    return results


class HybridRetriever:
    """Hybrid retrieval combining TF-IDF, BM25, and dense MiniLM+FAISS.

    Uses Reciprocal Rank Fusion to merge rankings from all three systems.
    Each subsystem is optional; the retriever degrades gracefully if one
    is unavailable.
    """

    def __init__(
        self,
        *,
        semantic_engine: SemanticSearchEngine,
        bm25_index: BM25Index,
        use_tfidf: bool = True,
        use_bm25: bool = True,
        use_dense: bool = True,
        top_k: int = 5,
    ):
        self.semantic_engine = semantic_engine
        self.bm25_index = bm25_index
        self.use_tfidf = use_tfidf
        self.use_bm25 = use_bm25
        self.use_dense = use_dense
        self.top_k = top_k

    def _tfidf_results(self, query: str) -> List[Dict[str, Any]]:
        if not self.use_tfidf:
            return []
        cases = simple_search(query)
        return [
            {
                "id": str(case.get("id", idx)),
                "case": case,
                "source": "tfidf",
            }
            for idx, case in enumerate(cases)
        ]

    def _bm25_results(self, query: str) -> List[Dict[str, Any]]:
        if not self.use_bm25:
            return []
        docs = self.bm25_index.search(query, top_k=self.top_k * 3)
        return [
            {
                "id": str(doc.get("id", idx)),
                "case": doc,
                "source": "bm25",
                "bm25_score": doc.get("bm25_score", 0.0),
            }
            for idx, doc in enumerate(docs)
        ]

    def _dense_results(self, query: str) -> List[Dict[str, Any]]:
        if not self.use_dense:
            return []
        hits = self.semantic_engine.search(query, top_k=self.top_k * 3)
        return [
            {
                "id": str(hit["case"].get("id", idx)),
                "case": hit["case"],
                "source": "dense",
                "semantic_score": hit.get("semantic_score", 0.0),
            }
            for idx, hit in enumerate(hits)
        ]

    def search(self, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        """Return hybrid-ranked results for a query.

        Each result is a case dict enriched with retrieval metadata
        (``rrf_score``, ``source``, per-system scores).
        """
        k = top_k or self.top_k
        if not query or not query.strip():
            return []

        lists: List[List[Dict[str, Any]]] = []

        tfidf = self._tfidf_results(query)
        if tfidf:
            lists.append(tfidf)

        bm25 = self._bm25_results(query)
        if bm25:
            lists.append(bm25)

        dense = self._dense_results(query)
        if dense:
            lists.append(dense)

        if not lists:
            return []

        fused = _rrf_rank(lists)

        # Enrich fused results: merge per-system scores into the case dict.
        enriched: List[Dict[str, Any]] = []
        for item in fused[:k]:
            case = dict(item.get("case", item))
            case["rrf_score"] = item.get("rrf_score", 0.0)
            case["retrieval_source"] = item.get("source", "hybrid")
            if "bm25_score" in item:
                case["bm25_score"] = item["bm25_score"]
            if "semantic_score" in item:
                case["semantic_score"] = item["semantic_score"]
            enriched.append(case)

        return enriched
