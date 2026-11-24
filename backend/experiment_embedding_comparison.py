"""NyaySaathi — Embedding model comparison experiment.

Tests alternative sentence-transformers models for legal text retrieval
using identical evaluation queries and labels.

Models tested:
1. sentence-transformers/all-MiniLM-L6-v2 (baseline, 384 dims)
2. sentence-transformers/all-mpnet-base-v2 (768 dims, generally better)
3. intfloat/multilingual-e5-base (768 dims, multilingual)
4. sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768 dims)

All models run on the same 201-case corpus with identical auto-generated queries.
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
from api.nlp.semantic_engine import SemanticSearchEngine
from evaluation import EvalQuery, aggregate, evaluate_single_query
from evaluation.dataset import build_auto_generated_dataset


MODELS = [
    ("sentence-transformers/all-MiniLM-L6-v2", 384),
    ("sentence-transformers/all-mpnet-base-v2", 768),
]


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


BACKEND = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent.parent / "experiment_results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_faiss_index(embeddings: np.ndarray, dimension: int) -> faiss.IndexFlatIP:
    """Build FAISS IndexFlatIP with L2-normalized vectors (cosine similarity)."""
    vectors = embeddings.astype("float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    vectors = vectors / norms
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)
    return index


def semantic_retrieve(
    index: faiss.IndexFlatIP,
    model: SentenceTransformer,
    cases: List[Dict[str, Any]],
    query: str,
    top_k: int = 5,
) -> List[str]:
    """Retrieve top-k case indices using semantic search."""
    qv = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    qv = np.asarray(qv, dtype="float32")[0]
    scores, indices = index.search(qv.reshape(1, -1), top_k)
    return [str(int(indices[0][i])) for i in range(top_k) if 0 <= indices[0][i] < len(cases)]


def evaluate_model(
    model_name: str,
    cases: List[Dict[str, Any]],
    queries: List[EvalQuery],
    top_k_values: List[int] = None,
) -> Dict[str, float]:
    """Evaluate a single embedding model."""
    if top_k_values is None:
        top_k_values = [1, 3, 5, 10]

    print(f"  Loading {model_name}...")
    model = SentenceTransformer(model_name)

    corpus_texts = [_build_searchable_text(c) for c in cases]
    embeddings = model.encode(
        corpus_texts, convert_to_numpy=True, normalize_embeddings=True,
        batch_size=32, show_progress_bar=False,
    )
    embeddings = np.asarray(embeddings, dtype="float32")
    dimension = int(embeddings.shape[1])
    index = build_faiss_index(embeddings, dimension)

    per_query = []
    for query in queries:
        retrieved_ids = semantic_retrieve(index, model, cases, query.query_text, top_k=10)
        result = evaluate_single_query(query, retrieved_ids)
        per_query.append(result)

    report = aggregate(per_query, model_name, "auto-generated")
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
        "models": {},
    }

    for model_name, dimension in MODELS:
        print(f"Testing {model_name} ({dimension} dims)...")
        t0 = time.perf_counter()
        metrics = evaluate_model(model_name, cases, queries)
        elapsed = time.perf_counter() - t0
        results["models"][model_name] = {
            **metrics,
            "dimensions": dimension,
            "load_and_eval_sec": round(elapsed, 2),
        }
        print(
            f"  {model_name}: R@5={metrics['recall@5']:.4f} "
            f"P@5={metrics['precision@5']:.4f} "
            f"MRR={metrics['mrr']:.4f} "
            f"nDCG@5={metrics['ndcg@5']:.4f} "
            f"({elapsed:.1f}s)"
        )

    out_path = OUT_DIR / "embedding_model_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
