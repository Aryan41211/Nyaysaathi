"""Retrieval evaluation runner for NyaySaathi.

Compares TF-IDF, BM25, dense MiniLM+FAISS, and hybrid retrieval using
identical queries and identical relevance labels. Results are clearly
tagged with label source (auto-generated vs human-validated).

Uses case index positions (0..N-1) as the canonical case ID across all
retrieval systems for consistent comparison.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from evaluation import (
    EvalQuery,
    EvalResult,
    EvaluationReport,
    aggregate,
    evaluate_single_query,
)
from evaluation.dataset import build_auto_generated_dataset
from api.data_loader import CASES
from api.nlp.bm25_index import BM25Index
from api.nlp.hybrid_retrieval import HybridRetriever
from api.nlp.semantic_engine import get_semantic_engine
from api.search_engine import simple_search


class RetrievalEvaluator:
    """Runs retrieval evaluation across multiple systems.

    All retrieval systems return case index positions (ints) as result IDs,
    matching the ``relevant_case_ids`` in evaluation queries which are also
    index positions.
    """

    def __init__(self, cases: List[Dict[str, Any]], queries: List[EvalQuery]):
        self.cases = cases
        self.queries = queries

        # Build a lookup from case content to index for mapping retrieval
        # results back to indices. We match on (category, subcategory,
        # problem_description) which is unique per case.
        self.case_to_index: Dict[str, int] = {}
        for idx, case in enumerate(cases):
            key = (
                str(case.get("category", "")).strip().lower(),
                str(case.get("subcategory", "")).strip().lower(),
                str(case.get("problem_description", "")).strip().lower(),
            )
            self.case_to_index[key] = idx

        # Initialize retrieval systems.
        self.semantic_engine = get_semantic_engine()
        self.semantic_engine.ensure_ready()
        self.bm25_index = BM25Index(cases)
        self.hybrid = HybridRetriever(
            semantic_engine=self.semantic_engine,
            bm25_index=self.bm25_index,
            use_tfidf=True,
            use_bm25=True,
            use_dense=True,
            top_k=5,
        )

    def _case_dict_to_index(self, case: Dict[str, Any]) -> int | None:
        """Map a retrieved case dict back to its index in CASES."""
        key = (
            str(case.get("category", "")).strip().lower(),
            str(case.get("subcategory", "")).strip().lower(),
            str(case.get("problem_description", "")).strip().lower(),
        )
        return self.case_to_index.get(key)

    def _tfidf_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        results = simple_search(query_text)
        indices: List[str] = []
        for case in results:
            idx = self._case_dict_to_index(case)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _bm25_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        results = self.bm25_index.search(query_text, top_k=top_k * 2)
        indices: List[str] = []
        for doc in results:
            idx = self._case_dict_to_index(doc)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _dense_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        hits = self.semantic_engine.search(query_text, top_k=top_k * 2)
        indices: List[str] = []
        for hit in hits:
            idx = self._case_dict_to_index(hit["case"])
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _hybrid_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        results = self.hybrid.search(query_text, top_k=top_k * 2)
        indices: List[str] = []
        for case in results:
            idx = self._case_dict_to_index(case)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _systems(self) -> Dict[str, Callable[[str, int], List[str]]]:
        return {
            "TF-IDF": self._tfidf_retrieve,
            "BM25": self._bm25_retrieve,
            "Dense (MiniLM+FAISS)": self._dense_retrieve,
            "Hybrid (TF-IDF+BM25+Dense + RRF)": self._hybrid_retrieve,
        }

    def run(self) -> Dict[str, EvaluationReport]:
        """Run evaluation on all systems using identical queries and labels.

        Returns:
            Dict mapping system name to EvaluationReport.
        """
        reports: Dict[str, EvaluationReport] = {}
        systems = self._systems()

        label_source = self.queries[0].label_source if self.queries else "auto-generated"

        for system_name, retrieve_fn in systems.items():
            per_query: List[EvalResult] = []
            for query in self.queries:
                retrieved_ids = retrieve_fn(query.query_text, top_k=10)
                result = evaluate_single_query(query, retrieved_ids)
                per_query.append(result)

            report = aggregate(per_query, system_name, label_source)
            reports[system_name] = report

        return reports

    def run_comparison(self) -> Dict[str, Any]:
        """Run evaluation and return a comparison summary dict."""
        reports = self.run()

        label_source = self.queries[0].label_source if self.queries else "auto-generated"

        summary: Dict[str, Any] = {
            "n_queries": len(self.queries),
            "label_source": label_source,
            "systems": {},
        }

        for name, report in reports.items():
            summary["systems"][name] = {
                "n_queries": report.n_queries,
                "metrics": report.metrics,
            }

        return summary


def run_evaluation_suite(cases: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function: build dataset and run full evaluation.

    Args:
        cases: Optional list of case dicts. Defaults to the loaded CASES.

    Returns:
        Comparison summary dict.
    """
    if cases is None:
        cases = CASES

    queries = build_auto_generated_dataset(cases)
    evaluator = RetrievalEvaluator(cases, queries)
    return evaluator.run_comparison()
