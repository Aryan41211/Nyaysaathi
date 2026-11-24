"""Hybrid retrieval for NyaySaathi.

Combines TF-IDF lexical, BM25 sparse, and MiniLM dense retrieval using
weighted score fusion. Falls back to Reciprocal Rank Fusion (RRF) when
weighted fusion is disabled. Each subsystem is optional; the retriever
degrades gracefully if one is unavailable.

Weighted fusion normalizes per-system scores to [0, 1] then combines with
tunable weights. Dense retrieval is given the highest weight since it
consistently outperforms lexical methods on this corpus.

Documents are matched across systems by content key
(category, subcategory, problem_description) since result IDs may differ
between retrieval subsystems.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from api.nlp.bm25_index import BM25Index
from api.nlp.faiss_index import FaissCaseIndex, SearchResult
from api.nlp.semantic_engine import SemanticSearchEngine
from api.search_engine import simple_search


def _case_content_key(case: Dict[str, Any]) -> Tuple[str, str, str]:
    """Stable content key for matching cases across retrieval systems."""
    return (
        str(case.get("category", "")).strip().lower(),
        str(case.get("subcategory", "")).strip().lower(),
        str(case.get("problem_description", "")).strip().lower(),
    )


def _normalize_scores(
    results: List[Dict[str, Any]], score_key: str
) -> List[Dict[str, Any]]:
    """Min-max normalize ``score_key`` values to [0, 1] within one result list.

    Returns a new list; input dicts are not mutated.
    """
    if not results:
        return []
    scores = [float(r.get(score_key, 0.0)) for r in results]
    s_min, s_max = min(scores), max(scores)
    span = s_max - s_min
    out: List[Dict[str, Any]] = []
    for r, s in zip(results, scores):
        norm = (s - s_min) / span if span > 0 else 0.0
        merged = dict(r)
        merged["_norm_score"] = norm
        out.append(merged)
    return out


def _weighted_fuse(
    system_results: Dict[str, List[Dict[str, Any]]],
    weights: Dict[str, float],
    score_key: str = "raw_score",
) -> List[Dict[str, Any]]:
    """Fuse per-system ranked lists using weighted normalized scores.

    Each system's raw scores are min-max normalized to [0, 1] independently,
    then combined as::

        fused = sum(w_sys * norm_score_sys) for each system containing the doc

    Docs appearing in multiple systems accumulate scores from each.
    Document matching uses the content key (category, subcategory,
    problem_description) so results from different subsystems align.
    """
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for sys_name, results in system_results.items():
        if not results:
            continue
        tagged: List[Dict[str, Any]] = []
        for r in results:
            merged = dict(r)
            merged["_system"] = sys_name
            merged["_raw_score"] = float(r.get(score_key, 0.0))
            merged["_content_key"] = _case_content_key(r.get("case", r))
            tagged.append(merged)
        normalized[sys_name] = _normalize_scores(tagged, "_raw_score")

    # Accumulate fused scores by content key.
    fused_scores: Dict[Tuple[str, str, str], float] = {}
    doc_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for sys_name, results in normalized.items():
        w = weights.get(sys_name, 0.0)
        for r in results:
            ck = r.get("_content_key")
            if ck is None:
                continue
            fused_scores[ck] = fused_scores.get(ck, 0.0) + w * r.get(
                "_norm_score", 0.0
            )
            doc_map[ck] = r

    fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    results: List[Dict[str, Any]] = []
    for ck, score in fused:
        doc = dict(doc_map[ck])
        doc["fused_score"] = float(score)
        doc["retrieval_source"] = doc.pop("_system", "hybrid")
        results.append(doc)
    return results


def _rrf_rank(
    ranked_lists: List[List[Any]], k: int = 60
) -> List[Any]:
    """Reciprocal Rank Fusion over multiple ranked result lists.

    Each list is a sequence of document dicts. Documents are matched by
    content key so results from different subsystems align.
    """
    scores: Dict[Tuple[str, str, str], float] = {}
    doc_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, start=1):
            ck = _case_content_key(doc.get("case", doc))
            scores[ck] = scores.get(ck, 0.0) + 1.0 / (k + rank)
            doc_map[ck] = doc

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results: List[Any] = []
    for ck, score in fused:
        doc = dict(doc_map[ck])
        doc["rrf_score"] = float(score)
        results.append(doc)

    return results


class HybridRetriever:
    """Hybrid retrieval combining TF-IDF lexical, BM25 sparse, and dense
    MiniLM+FAISS using weighted score fusion (default) or RRF.

    Dense retrieval is weighted highest (0.6) since it consistently
    outperforms lexical methods on this corpus. Weights are configurable.
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
        fusion: str = "weighted",
        weights: Optional[Dict[str, float]] = None,
        reranker: Optional[Any] = None,
        rerank_top_n: int = 20,
    ):
        self.semantic_engine = semantic_engine
        self.bm25_index = bm25_index
        self.use_tfidf = use_tfidf
        self.use_bm25 = use_bm25
        self.use_dense = use_dense
        self.top_k = top_k
        self.fusion = fusion
        # Default: dense-heavy fusion since dense is strongest on this corpus.
        self.weights = weights or {
            "tfidf": 0.10,
            "bm25": 0.30,
            "dense": 0.60,
        }
        self.reranker = reranker
        self.rerank_top_n = rerank_top_n

    def _tfidf_results(self, query: str) -> List[Dict[str, Any]]:
        if not self.use_tfidf:
            return []
        cases = simple_search(query)
        return [
            {
                "case": case,
                "source": "tfidf",
                "raw_score": 1.0,
            }
            for case in cases
        ]

    def _bm25_results(self, query: str) -> List[Dict[str, Any]]:
        if not self.use_bm25:
            return []
        docs = self.bm25_index.search(query, top_k=self.top_k * 3)
        return [
            {
                "case": doc,
                "source": "bm25",
                "raw_score": float(doc.get("bm25_score", 0.0)),
            }
            for doc in docs
        ]

    def _dense_results(self, query: str) -> List[Dict[str, Any]]:
        if not self.use_dense:
            return []
        hits = self.semantic_engine.search(query, top_k=self.top_k * 3)
        return [
            {
                "case": hit["case"],
                "source": "dense",
                "raw_score": float(hit.get("semantic_score", 0.0)),
            }
            for hit in hits
        ]

    def _rerank(
        self, query: str, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Optionally re-rank top candidates with a cross-encoder.

        ``reranker`` must expose ``rank(query, docs) -> List[float]`` where
        ``docs`` is a list of text strings and the return is a list of scores.
        """
        if self.reranker is None or not results:
            return results
        docs = [r.get("case", {}).get("searchable_text", "") for r in results]
        try:
            scores = self.reranker.rank(query, docs, top_n=self.rerank_top_n)
        except Exception:
            # Reranker failure is non-fatal: return un-re-ranked results.
            return results
        if scores and isinstance(scores[0], (list, tuple)):
            ordered = sorted(scores, key=lambda x: x[1], reverse=True)
            reranked: List[Dict[str, Any]] = []
            for idx, score in ordered:
                if idx < len(results):
                    doc = dict(results[idx])
                    doc["rerank_score"] = float(score)
                    reranked.append(doc)
            return reranked
        return results

    def search(self, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        """Return hybrid-ranked results for a query.

        Each result is a case dict enriched with retrieval metadata
        (``fused_score`` or ``rrf_score``, ``source``, per-system scores).
        """
        k = top_k or self.top_k
        if not query or not query.strip():
            return []

        system_results: Dict[str, List[Dict[str, Any]]] = {}

        tfidf = self._tfidf_results(query)
        if tfidf:
            system_results["tfidf"] = tfidf

        bm25 = self._bm25_results(query)
        if bm25:
            system_results["bm25"] = bm25

        dense = self._dense_results(query)
        if dense:
            system_results["dense"] = dense

        if not system_results:
            return []

        if self.fusion == "weighted":
            fused = _weighted_fuse(system_results, self.weights, score_key="raw_score")
        else:
            lists = [system_results[s] for s in system_results]
            fused = _rrf_rank(lists)

        # Optional cross-encoder re-ranking on top candidates.
        pre_rerank = fused[: self.rerank_top_n]
        reranked = self._rerank(query, pre_rerank)
        final = reranked + fused[self.rerank_top_n :]

        # Enrich fused results: merge per-system scores into the case dict.
        enriched: List[Dict[str, Any]] = []
        for item in final[:k]:
            case = dict(item.get("case", item))
            if "fused_score" in item:
                case["fused_score"] = item["fused_score"]
            if "rrf_score" in item:
                case["rrf_score"] = item["rrf_score"]
            if "rerank_score" in item:
                case["rerank_score"] = item["rerank_score"]
            if "bm25_score" in item:
                case["bm25_score"] = item["bm25_score"]
            if "semantic_score" in item:
                case["semantic_score"] = item["semantic_score"]
            case["retrieval_source"] = item.get("retrieval_source", "hybrid")
            enriched.append(case)

        return enriched
