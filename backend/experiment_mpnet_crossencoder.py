"""NyaySaathi — MPNet + Cross-Encoder experiment.

Tests MPNet embeddings with optional cross-encoder reranking.
Compares against MiniLM baseline using identical queries and labels.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentence_transformers import CrossEncoder, SentenceTransformer
import numpy as np
import faiss

from api.data_loader import CASES
from evaluation import EvalQuery, aggregate, evaluate_single_query
from evaluation.dataset import build_auto_generated_dataset


def _build_searchable_text(case: Dict[str, Any]) -> str:
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


class Retriever:
    def __init__(
        self,
        model_name: str,
        use_reranker: bool = False,
        top_k: int = 5,
    ):
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = int(self.model.get_sentence_embedding_dimension())
        self.use_reranker = use_reranker
        self.top_k = top_k
        self.reranker = None
        if use_reranker:
            self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
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
        search_k = min(k * 5, len(self._cases))
        scores, indices = self._index.search(qv.reshape(1, -1), search_k)

        hits = []
        for i in range(len(indices[0])):
            idx = int(indices[0][i])
            if 0 <= idx < len(self._cases):
                hits.append({
                    "case": self._cases[idx],
                    "raw_score": float(scores[0][i]),
                })

        if self.use_reranker and self.reranker is not None and hits:
            docs = [h["case"].get("searchable_text", _build_searchable_text(h["case"])) for h in hits]
            rerank_scores = self.reranker.predict([(query, d) for d in docs])
            ranked = sorted(zip(hits, rerank_scores), key=lambda x: x[1], reverse=True)
            hits = [{"case": h["case"], "raw_score": float(s), "rerank_score": float(s)} for h, s in ranked[:k]]
        else:
            hits = hits[:k]

        return hits


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
            str(retriever._cases.index(r["case"])) for r in results
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
        ("MiniLM (baseline)", {"model_name": "sentence-transformers/all-MiniLM-L6-v2", "use_reranker": False}),
        ("MPNet", {"model_name": "sentence-transformers/all-mpnet-base-v2", "use_reranker": False}),
        ("MPNet + CrossEncoder", {"model_name": "sentence-transformers/all-mpnet-base-v2", "use_reranker": True}),
    ]

    for name, config in configs:
        print(f"Testing {name}...")
        t0 = time.perf_counter()
        retriever = Retriever(**config)
        metrics = evaluate_retriever(name, retriever, queries)
        elapsed = time.perf_counter() - t0
        results["configs"][name] = {
            **metrics,
            "model_name": config["model_name"],
            "use_reranker": config["use_reranker"],
            "eval_sec": round(elapsed, 2),
        }
        print(
            f"  {name}: R@5={metrics['recall@5']:.4f} "
            f"P@5={metrics['precision@5']:.4f} "
            f"MRR={metrics['mrr']:.4f} "
            f"nDCG@5={metrics['ndcg@5']:.4f} "
            f"({elapsed:.1f}s)"
        )

    out_path = Path(__file__).resolve().parent.parent / "experiment_results" / "mpnet_crossencoder_comparison.json"
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
