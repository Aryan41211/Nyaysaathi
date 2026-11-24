"""NyaySaathi retrieval experiment runner.

Compares multiple fusion configurations using identical queries and labels.
Designed for ablation experiments per Phase A4 of the optimization program.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation import EvalQuery, aggregate, evaluate_single_query
from evaluation.dataset import build_auto_generated_dataset
from api.data_loader import CASES
from api.nlp.bm25_index import BM25Index
from api.nlp.cross_encoder_reranker import CrossEncoderReranker
from api.nlp.hybrid_retrieval import HybridRetriever
from api.nlp.semantic_engine import get_semantic_engine
from api.search_engine import simple_search

from typing import Dict


def _load_cases(corpus_path: str | None = None) -> List[Dict[str, Any]]:
    if corpus_path:
        import json
        with open(corpus_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return CASES


class RetrievalEvaluator:
    """Runs retrieval evaluation across multiple fusion configurations."""

    def __init__(self, cases: List[Dict[str, Any]], queries: List[EvalQuery]):
        self.cases = cases
        self.queries = queries
        self.semantic_engine = get_semantic_engine()
        self.semantic_engine.ensure_ready()
        self.bm25_index = BM25Index(cases)

        # Build content-key to index mapping for matching retrieved cases
        # back to evaluation query relevance judgments.
        self.key_to_index: Dict[Tuple[str, str, str], int] = {}
        for idx, case in enumerate(cases):
            key = (
                str(case.get("category", "")).strip().lower(),
                str(case.get("subcategory", "")).strip().lower(),
                str(case.get("problem_description", "")).strip().lower(),
            )
            self.key_to_index[key] = idx

    def _case_to_index(self, case: Dict[str, Any]) -> int | None:
        key = (
            str(case.get("category", "")).strip().lower(),
            str(case.get("subcategory", "")).strip().lower(),
            str(case.get("problem_description", "")).strip().lower(),
        )
        return self.key_to_index.get(key)

    def _tfidf_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        results = simple_search(query_text)
        indices: List[str] = []
        for case in results:
            idx = self._case_to_index(case)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _bm25_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        results = self.bm25_index.search(query_text, top_k=top_k * 2)
        indices: List[str] = []
        for doc in results:
            idx = self._case_to_index(doc)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _dense_retrieve(self, query_text: str, top_k: int = 5) -> List[str]:
        hits = self.semantic_engine.search(query_text, top_k=top_k * 2)
        indices: List[str] = []
        for hit in hits:
            idx = self._case_to_index(hit["case"])
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def _make_retriever(
        self,
        fusion: str = "weighted",
        weights: Dict[str, float] = None,
        use_tfidf: bool = True,
        use_bm25: bool = True,
        use_dense: bool = True,
        reranker: Any = None,
        rerank_top_n: int = 20,
    ) -> HybridRetriever:
        return HybridRetriever(
            semantic_engine=self.semantic_engine,
            bm25_index=self.bm25_index,
            use_tfidf=use_tfidf,
            use_bm25=use_bm25,
            use_dense=use_dense,
            top_k=10,
            fusion=fusion,
            weights=weights,
            reranker=reranker,
            rerank_top_n=rerank_top_n,
        )

    def _retrieve_with(
        self, retriever: HybridRetriever, query_text: str, top_k: int = 10
    ) -> List[str]:
        results = retriever.search(query_text, top_k=top_k)
        indices: List[str] = []
        for item in results:
            case = item.get("case", item)
            idx = self._case_to_index(case)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def run_config(
        self,
        name: str,
        retriever: HybridRetriever,
        top_k_values: List[int] = None,
    ) -> Dict[str, float]:
        """Run evaluation for a single configuration and return metrics dict."""
        if top_k_values is None:
            top_k_values = [1, 3, 5, 10]

        per_query = []
        for query in self.queries:
            retrieved_ids = self._retrieve_with(retriever, query.query_text, top_k=10)
            result = evaluate_single_query(query, retrieved_ids)
            per_query.append(result)

        report = aggregate(per_query, name, "auto-generated")
        metrics: Dict[str, float] = {}
        for k in top_k_values:
            metrics[f"recall@{k}"] = report.metrics.get(f"recall@{k}", 0.0)
            metrics[f"precision@{k}"] = report.metrics.get(f"precision@{k}", 0.0)
            metrics[f"ndcg@{k}"] = report.metrics.get(f"ndcg@{k}", 0.0)
        metrics["mrr"] = report.metrics.get("mrr", 0.0)
        return metrics

    def run_all(self) -> Dict[str, Any]:
        """Run all fusion configurations and return comparison."""
        # Try to load cross-encoder reranker (may fail if no internet/model cache)
        try:
            reranker = CrossEncoderReranker()
            reranker_available = reranker.is_loaded or reranker._load_model()
        except Exception:
            reranker = None
            reranker_available = False

        if reranker_available:
            print(f"  Cross-encoder reranker loaded: {reranker.model_name}")
        else:
            print("  Cross-encoder reranker NOT available (skipping rerank experiments)")

        configs = [
            ("Dense only", self._make_retriever(fusion="weighted", weights={"tfidf": 0.0, "bm25": 0.0, "dense": 1.0}, use_tfidf=False, use_bm25=False)),
            ("BM25 only", self._make_retriever(fusion="weighted", weights={"tfidf": 0.0, "bm25": 1.0, "dense": 0.0}, use_tfidf=False, use_dense=False)),
            ("TF-IDF only", self._make_retriever(fusion="weighted", weights={"tfidf": 1.0, "bm25": 0.0, "dense": 0.0}, use_bm25=False, use_dense=False)),
            ("RRF (k=60)", self._make_retriever(fusion="rrf")),
            ("Weighted 0.7/0.2/0.1", self._make_retriever(fusion="weighted", weights={"tfidf": 0.1, "bm25": 0.2, "dense": 0.7})),
        ]

        if reranker_available:
            configs.extend([
                ("Weighted 0.7/0.2/0.1 + CrossEncoder", self._make_retriever(
                    fusion="weighted",
                    weights={"tfidf": 0.1, "bm25": 0.2, "dense": 0.7},
                    reranker=reranker,
                    rerank_top_n=20,
                )),
                ("Dense + CrossEncoder", self._make_retriever(
                    fusion="weighted",
                    weights={"tfidf": 0.0, "bm25": 0.0, "dense": 1.0},
                    use_tfidf=False,
                    use_bm25=False,
                    reranker=reranker,
                    rerank_top_n=20,
                )),
            ])

        results: Dict[str, Any] = {
            "n_queries": len(self.queries),
            "label_source": "auto-generated",
            "configs": {},
            "reranker_available": reranker_available,
            "reranker_model": reranker.model_name if reranker_available else None,
        }

        for name, retriever in configs:
            metrics = self.run_config(name, retriever)
            results["configs"][name] = metrics
            print(
                f"  {name}: R@5={metrics['recall@5']:.4f} "
                f"P@5={metrics['precision@5']:.4f} "
                f"MRR={metrics['mrr']:.4f} "
                f"nDCG@5={metrics['ndcg@5']:.4f}"
            )

        return results


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="NyaySaathi retrieval evaluation benchmark")
    parser.add_argument(
        "--corpus", help="Path to corpus JSON file (default: backend/dataset/legal_cases.json)"
    )
    args = parser.parse_args()

    cases = _load_cases(args.corpus)
    queries = build_auto_generated_dataset(cases)
    evaluator = RetrievalEvaluator(cases, queries)
    results = evaluator.run_all()

    out_path = Path(__file__).resolve().parent.parent / "experiment_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
