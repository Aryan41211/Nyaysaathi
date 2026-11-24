"""NyaySaathi — MPNet + Hybrid Fusion experiment.

Tests MPNet embeddings combined with weighted hybrid fusion (TF-IDF + BM25 + dense).
Compares against MiniLM baseline to measure combined improvement.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

from api.data_loader import CASES
from api.nlp.bm25_index import BM25Index
from api.nlp.hybrid_retrieval import HybridRetriever
from api.nlp.semantic_engine import SemanticSearchEngine, get_semantic_engine
from evaluation import EvalQuery, aggregate, evaluate_single_query
from evaluation.dataset import build_auto_generated_dataset


def _build_searchable_text(case: Dict[str, Any]) -> str:
    """Build searchable text the same way semantic_engine._normalize_case does."""
    chunks = [
        str(case.get("category", "")),
        str(case.get("subcategory", "")),
        str(case.get("problem_description", "")),
    ]
    descriptions = case.get("descriptions", [])
    if isinstance(descriptions, list):
        chunks.append(" ".join(str(x) for x in descriptions))
    workflow_steps = case.get("workflow_steps", [])
    if isinstance(workflow_steps, list):
        chunks.append(" ".join(str(x) for x in workflow_steps))
    return " ".join(chunk for chunk in chunks if chunk).strip()


class MPNetHybridRetriever:
    """Hybrid retriever using MPNet embeddings with weighted fusion."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        weights: Dict[str, float] = None,
        top_k: int = 5,
    ):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = int(self.model.get_sentence_embedding_dimension())
        self.bm25_index = BM25Index(CASES)
        self.weights = weights or {"tfidf": 0.1, "bm25": 0.2, "dense": 0.7}
        self.top_k = top_k
        self._index = None
        self._build_index(CASES)

    def _build_index(self, cases: List[Dict[str, Any]]):
        corpus_texts = [_build_searchable_text(c) for c in cases]
        embeddings = self.model.encode(
            corpus_texts, convert_to_numpy=True, normalize_embeddings=True,
            batch_size=32, show_progress_bar=False,
        )
        embeddings = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(self.dimension)
        index.add(embeddings)
        self._index = index
        self._cases = cases

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        k = top_k or self.top_k
        qv = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        qv = np.asarray(qv, dtype="float32")[0]
        scores, indices = self._index.search(qv.reshape(1, -1), min(k * 3, len(self._cases)))

        dense_results = []
        for i in range(len(indices[0])):
            idx = int(indices[0][i])
            if 0 <= idx < len(self._cases):
                dense_results.append({
                    "case": self._cases[idx],
                    "source": "dense",
                    "raw_score": float(scores[0][i]),
                })

        # Build system results dict for weighted fusion
        system_results = {"dense": dense_results}

        # Add TF-IDF and BM25 results
        from api.search_engine import simple_search
        tfidf_cases = simple_search(query)
        system_results["tfidf"] = [
            {"case": case, "source": "tfidf", "raw_score": 1.0}
            for case in tfidf_cases
        ]

        bm25_docs = self.bm25_index.search(query, top_k=k * 3)
        system_results["bm25"] = [
            {"case": doc, "source": "bm25", "raw_score": float(doc.get("bm25_score", 0.0))}
            for doc in bm25_docs
        ]

        # Weighted fusion
        fused = _weighted_fuse(system_results, self.weights, score_key="raw_score")

        # Enrich results
        enriched = []
        for item in fused[:k]:
            case = dict(item.get("case", item))
            case["fused_score"] = item.get("fused_score", 0.0)
            case["retrieval_source"] = item.get("retrieval_source", "hybrid")
            enriched.append(case)

        return enriched


def _normalize_scores(
    results: List[Dict[str, Any]], score_key: str
) -> List[Dict[str, Any]]:
    if not results:
        return []
    scores = [float(r.get(score_key, 0.0)) for r in results]
    s_min, s_max = min(scores), max(scores)
    span = s_max - s_min
    out = []
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
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for sys_name, results in system_results.items():
        if not results:
            continue
        tagged = []
        for r in results:
            merged = dict(r)
            merged["_system"] = sys_name
            merged["_raw_score"] = float(r.get(score_key, 0.0))
            merged["_content_key"] = (
                str(merged.get("case", {}).get("category", "")).strip().lower(),
                str(merged.get("case", {}).get("subcategory", "")).strip().lower(),
                str(merged.get("case", {}).get("problem_description", "")).strip().lower(),
            )
            tagged.append(merged)
        normalized[sys_name] = _normalize_scores(tagged, "_raw_score")

    fused_scores: Dict[tuple, float] = {}
    doc_map: Dict[tuple, Dict[str, Any]] = {}
    for sys_name, results in normalized.items():
        w = weights.get(sys_name, 0.0)
        for r in results:
            ck = r.get("_content_key")
            if ck is None:
                continue
            fused_scores[ck] = fused_scores.get(ck, 0.0) + w * r.get("_norm_score", 0.0)
            doc_map[ck] = r

    fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for ck, score in fused:
        doc = dict(doc_map[ck])
        doc["fused_score"] = float(score)
        doc["retrieval_source"] = doc.pop("_system", "hybrid")
        results.append(doc)
    return results


def evaluate_retriever(
    name: str,
    retriever: Any,
    queries: List[EvalQuery],
    top_k_values: List[int] = None,
) -> Dict[str, float]:
    if top_k_values is None:
        top_k_values = [1, 3, 5, 10]

    per_query = []
    for query in queries:
        results = retriever.search(query.query_text, top_k=10)
        retrieved_ids = [
            str(case.get("id", idx)) for idx, case in enumerate(results)
        ]
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


def main() -> int:
    cases = CASES
    queries = build_auto_generated_dataset(cases)

    print(f"Corpus: {len(cases)} cases, {len(queries)} evaluation queries\n")

    results: Dict[str, Any] = {
        "n_queries": len(queries),
        "label_source": "auto-generated",
        "configs": {},
    }

    configs = [
        ("MiniLM + Weighted Hybrid", lambda: HybridRetriever(
            semantic_engine=get_semantic_engine(),
            bm25_index=BM25Index(CASES),
            use_tfidf=True, use_bm25=True, use_dense=True,
            top_k=5, fusion="weighted",
            weights={"tfidf": 0.1, "bm25": 0.2, "dense": 0.7},
        )),
        ("MPNet + Weighted Hybrid", lambda: MPNetHybridRetriever(
            model_name="sentence-transformers/all-mpnet-base-v2",
            weights={"tfidf": 0.1, "bm25": 0.2, "dense": 0.7},
            top_k=5,
        )),
        ("MPNet + Weighted Hybrid + CrossEncoder", None),  # Skip - too slow, already tested
    ]

    for name, retriever_fn in configs:
        if retriever_fn is None:
            continue
        print(f"Testing {name}...")
        t0 = time.perf_counter()
        retriever = retriever_fn()
        metrics = evaluate_retriever(name, retriever, queries)
        elapsed = time.perf_counter() - t0
        results["configs"][name] = {
            **metrics,
            "eval_sec": round(elapsed, 2),
        }
        print(
            f"  {name}: R@5={metrics['recall@5']:.4f} "
            f"P@5={metrics['precision@5']:.4f} "
            f"MRR={metrics['mrr']:.4f} "
            f"nDCG@5={metrics['ndcg@5']:.4f} "
            f"({elapsed:.1f}s)"
        )

    out_path = Path(__file__).resolve().parent.parent / "experiment_results" / "mpnet_hybrid_comparison.json"
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
