"""NyaySaathi — Embedding model comparison benchmark.

Compares MiniLM vs MPNet embeddings using identical evaluation queries and labels.
All retrieval uses the same corpus for consistency.
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
    """Simple retriever with a specific embedding model for fair comparison."""

    def __init__(self, model_name: str, cases: List[Dict[str, Any]]):
        self.model_name = model_name
        self.cases = cases
        self.model = SentenceTransformer(model_name)
        self.dimension = int(self.model.get_sentence_embedding_dimension())
        self._build_index(cases)

    def _build_index(self, cases: List[Dict[str, Any]]):
        corpus_texts = [_build_searchable_text(c) for c in cases]
        embeddings = self.model.encode(
            corpus_texts, convert_to_numpy=True, normalize_embeddings=True,
            batch_size=32, show_progress_bar=False,
        )
        self.embeddings = np.asarray(embeddings, dtype="float32")
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(self.embeddings)

    def search(self, query: str, top_k: int = 5) -> List[str]:
        qv = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        qv = np.asarray(qv, dtype="float32")[0]
        scores, indices = self.index.search(qv.reshape(1, -1), min(top_k, len(self.cases)))
        return [str(int(indices[0][i])) for i in range(len(indices[0])) if 0 <= int(indices[0][i]) < len(self.cases)]


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
        retrieved_ids = retriever.search(query.query_text, top_k=10)
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
    import argparse

    parser = argparse.ArgumentParser(description="NyaySaathi embedding model comparison")
    parser.add_argument(
        "--corpus", default="dataset/expanded_cases.json",
        help="Path to corpus JSON file"
    )
    args = parser.parse_args()

    with open(Path(__file__).resolve().parent / args.corpus, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Corpus: {len(cases)} cases")

    queries = build_auto_generated_dataset(cases)
    print(f"Evaluation queries: {len(queries)}")

    results: Dict[str, Any] = {
        "n_queries": len(queries),
        "corpus_size": len(cases),
        "corpus_file": args.corpus,
        "configs": {},
    }

    configs = [
        ("MiniLM (all-MiniLM-L6-v2, 384d)", "sentence-transformers/all-MiniLM-L6-v2"),
        ("MPNet (all-mpnet-base-v2, 768d)", "sentence-transformers/all-mpnet-base-v2"),
    ]

    for name, model_name in configs:
        print(f"\nTesting {name}...")
        t0 = time.perf_counter()
        retriever = Retriever(model_name, cases)
        load_time = time.perf_counter() - t0
        print(f"  Model loaded in {load_time:.1f}s")

        metrics = evaluate_retriever(name, retriever, queries)
        results["configs"][name] = {
            **metrics,
            "model_name": model_name,
            "eval_sec": round(time.perf_counter() - t0, 2),
        }
        print(
            f"  {name}: R@5={metrics['recall@5']:.4f} "
            f"P@5={metrics['precision@5']:.4f} "
            f"MRR={metrics['mrr']:.4f} "
            f"nDCG@5={metrics['ndcg@5']:.4f}"
        )

    out_path = Path(__file__).resolve().parent.parent / "experiment_results" / "model_comparison.json"
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
