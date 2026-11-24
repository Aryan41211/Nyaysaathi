"""NyaySaathi Phase 2 — Comprehensive Retrieval Benchmark.

Compares MiniLM vs MPNet embeddings using:
  - Auto-generated labels (500-case corpus proxy)
  - Human-validated labels (50 curated queries, all 10 categories)
Measures p50/p95/p99 latency for end-to-end retrieval.

Results written to experiment_results/phase2_benchmark.json
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from api.nlp.semantic_engine import get_semantic_engine, SemanticSearchEngine
from api.nlp.bm25_index import BM25Index
from api.nlp.hybrid_retrieval import HybridRetriever
from api.search_engine import simple_search
from evaluation import (
    EvalQuery,
    evaluate_single_query,
    aggregate,
)
from evaluation.dataset import build_auto_generated_dataset


BACKEND = Path(__file__).resolve().parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)


def _build_searchable_text(case: Dict[str, Any]) -> str:
    chunks = [
        str(case.get("category", "")),
        str(case.get("subcategory", "")),
        str(case.get("problem_description", "")),
    ]
    for key in ("descriptions", "workflow_steps"):
        val = case.get(key, [])
        if isinstance(val, list):
            chunks.append(" ".join(str(x) for x in val))
    return " ".join(chunk for chunk in chunks if chunk).strip()


def _case_to_index_key(case: Dict[str, Any]) -> tuple:
    return (
        str(case.get("category", "")).strip().lower(),
        str(case.get("subcategory", "")).strip().lower(),
        str(case.get("problem_description", "")).strip().lower(),
    )


class EmbeddingRetriever:
    """Dense retriever backed by a specific sentence-transformers model."""

    def __init__(self, model_name: str, cases: List[Dict[str, Any]]):
        self.model_name = model_name
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }
        print(f"  Loading {model_name} ...", flush=True)
        self.model = SentenceTransformer(model_name)
        self.dim = int(self.model.get_sentence_embedding_dimension())
        self._build_index()
        print(f"    dim={self.dim}, n_cases={len(cases)}", flush=True)

    def _build_index(self):
        texts = [_build_searchable_text(c) for c in self.cases]
        vecs = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        self.embeddings = np.asarray(vecs, dtype="float32")
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(self.embeddings)

    def search(self, query: str, top_k: int = 5) -> List[str]:
        qv = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        qv = np.asarray(qv, dtype="float32")[0]
        k = min(top_k, len(self.cases))
        scores, indices = self.index.search(qv.reshape(1, -1), k)
        return [
            str(int(indices[0][i]))
            for i in range(len(indices[0]))
            if 0 <= int(indices[0][i]) < len(self.cases)
        ]

    def search_with_latency(self, query: str, top_k: int = 5) -> tuple:
        """Returns (indices, latency_ms)."""
        t0 = time.perf_counter()
        indices = self.search(query, top_k=top_k)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return indices, latency_ms


class HybridRetrieverWrapper:
    """Wraps the existing HybridRetriever to return case indices."""

    def __init__(self, cases: List[Dict[str, Any]]):
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }
        engine = get_semantic_engine()
        engine.ensure_ready()
        bm25_index = BM25Index(cases)
        self.hybrid = HybridRetriever(
            semantic_engine=engine,
            bm25_index=bm25_index,
            use_tfidf=True,
            use_bm25=True,
            use_dense=True,
            top_k=5,
            fusion="weighted",
            weights={"tfidf": 0.1, "bm25": 0.2, "dense": 0.7},
        )

    def search(self, query: str, top_k: int = 5) -> List[str]:
        results = self.hybrid.search(query, top_k=top_k * 2)
        indices = []
        for item in results:
            case = item.get("case", item)
            key = _case_to_index_key(case)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    def search_with_latency(self, query: str, top_k: int = 5) -> tuple:
        t0 = time.perf_counter()
        indices = self.search(query, top_k=top_k)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return indices, latency_ms


class TFIDFRetrieverWrapper:
    def __init__(self, cases: List[Dict[str, Any]]):
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }

    def search(self, query: str, top_k: int = 5) -> List[str]:
        results = simple_search(query)
        indices = []
        for case in results:
            key = _case_to_index_key(case)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]


def load_human_validated_dataset() -> List[EvalQuery]:
    path = BACKEND / "evaluation" / "datasets" / "human_validated.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    queries: List[EvalQuery] = []
    for item in data.get("queries", []):
        queries.append(
            EvalQuery(
                query_id=item["query_id"],
                query_text=item["query_text"],
                relevant_case_ids=list(item.get("relevant_case_ids", [])),
                relevance_grades=item.get("relevance_grades", {}),
                label_source="human-validated",
                metadata=item.get("metadata", {}),
            )
        )
    return queries


def _percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    s = sorted(sorted_vals)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    d = k - f
    return s[f] + (s[c] - s[f]) * d


def run_benchmark() -> Dict[str, Any]:
    engine = get_semantic_engine()
    engine.ensure_ready()
    cases = engine.get_cases()
    print(f"Loaded {len(cases)} deduplicated cases from semantic engine", flush=True)

    # Auto-generated queries from deduplicated corpus
    auto_queries = build_auto_generated_dataset(cases)
    print(f"Auto-generated queries: {len(auto_queries)}", flush=True)

    # Human-validated queries — need to map their case indices
    # Human-validated dataset references indices into the 500-case expanded_cases.json.
    # We need to map those to indices in the deduplicated `cases` list.
    # Build a mapping from original index -> deduped index by matching content.
    with open(BACKEND / "dataset" / "expanded_cases.json", "r", encoding="utf-8") as f:
        expanded_cases = json.load(f)

    expanded_to_deduped: Dict[int, int] = {}
    deduped_keys = {_case_to_index_key(c): i for i, c in enumerate(cases)}
    for orig_idx, case in enumerate(expanded_cases):
        key = _case_to_index_key(case)
        if key in deduped_keys:
            expanded_to_deduped[orig_idx] = deduped_keys[key]

    human_raw = load_human_validated_dataset()
    human_queries: List[EvalQuery] = []
    for q in human_raw:
        mapped_ids = []
        for cid_str in q.relevant_case_ids:
            orig_idx = int(cid_str)
            if orig_idx in expanded_to_deduped:
                mapped_ids.append(str(expanded_to_deduped[orig_idx]))
        if mapped_ids:
            human_queries.append(
                EvalQuery(
                    query_id=q.query_id,
                    query_text=q.query_text,
                    relevant_case_ids=mapped_ids,
                    relevance_grades=q.relevance_grades,
                    label_source="human-validated",
                    metadata=q.metadata,
                )
            )
    print(f"Human-validated queries (mapped): {len(human_queries)}", flush=True)

    # --- Retrieval systems ---
    systems = {
        "TF-IDF": TFIDFRetrieverWrapper(cases),
        "BM25": None,  # built below
        "Dense (MiniLM 384d)": EmbeddingRetriever(
            "sentence-transformers/all-MiniLM-L6-v2", cases
        ),
        "Dense (MPNet 768d)": EmbeddingRetriever(
            "sentence-transformers/all-mpnet-base-v2", cases
        ),
        "Hybrid (weighted fusion)": HybridRetrieverWrapper(cases),
    }
    systems["BM25"] = None  # placeholder; BM25Index used via HybridRetriever
    # Use BM25Index directly for a pure BM25 system
    bm25_index = BM25Index(cases)

    def bm25_search(query: str, top_k: int = 5) -> List[str]:
        results = bm25_index.search(query, top_k=top_k * 2)
        indices = []
        for doc in results:
            key = _case_to_index_key(doc)
            idx = systems["TF-IDF"].case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]

    # --- Evaluation helper ---
    def evaluate_system(name: str, retrieve_fn, queries: List[EvalQuery]) -> Dict[str, float]:
        per_query = []
        for query in queries:
            retrieved = retrieve_fn(query.query_text, top_k=10)
            result = evaluate_single_query(query, retrieved)
            per_query.append(result)
        report = aggregate(per_query, name, queries[0].label_source if queries else "unknown")
        return report.metrics

    # --- Latency benchmark ---
    def latency_benchmark(name: str, retrieve_fn, n_queries: int = 50) -> Dict[str, float]:
        latencies: List[float] = []
        test_queries = auto_queries[:n_queries]
        for query in test_queries:
            if hasattr(retrieve_fn, 'search_with_latency'):
                _, lat = retrieve_fn.search_with_latency(query.query_text, top_k=5)
            elif callable(getattr(retrieve_fn, 'search', None)) and not hasattr(retrieve_fn, '__call__'):
                # retriever object with .search method (returns list)
                t0 = time.perf_counter()
                retrieve_fn.search(query.query_text, top_k=5)
                lat = (time.perf_counter() - t0) * 1000.0
            else:
                # plain callable
                t0 = time.perf_counter()
                retrieve_fn(query.query_text, top_k=5)
                lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
        latencies.sort()
        return {
            "p50_ms": round(_percentile(latencies, 50), 2),
            "p90_ms": round(_percentile(latencies, 90), 2),
            "p95_ms": round(_percentile(latencies, 95), 2),
            "p99_ms": round(_percentile(latencies, 99), 2),
            "mean_ms": round(statistics.mean(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
        }

    # Build retriever objects with latency support
    retrievers = {
        "TF-IDF": TFIDFRetrieverWrapper(cases),
        "BM25": bm25_index,  # has .search but no latency wrapper
        "Dense (MiniLM 384d)": systems["Dense (MiniLM 384d)"],
        "Dense (MPNet 768d)": systems["Dense (MPNet 768d)"],
        "Hybrid (weighted fusion)": HybridRetrieverWrapper(cases),
    }

    results: Dict[str, Any] = {
        "n_deduped_cases": len(cases),
        "n_auto_queries": len(auto_queries),
        "n_human_queries": len(human_queries),
        "systems": {},
    }

    # Evaluate each system on auto-generated labels
    for name, retr in retrievers.items():
        print(f"\nEvaluating {name} on auto-generated labels ...", flush=True)

        if name == "BM25":
            def bm25_fn(query_text, top_k=5):
                docs = bm25_index.search(query_text, top_k=top_k * 2)
                idxs = []
                for d in docs:
                    key = _case_to_index_key(d)
                    i = retrievers["TF-IDF"].case_to_index.get(key)
                    if i is not None:
                        idxs.append(str(i))
                return idxs[:top_k]
            metrics = evaluate_system(name, bm25_fn, auto_queries)
            # latency for BM25
            latencies = []
            for query in auto_queries[:50]:
                t0 = time.perf_counter()
                bm25_fn(query.query_text, top_k=5)
                latencies.append((time.perf_counter() - t0) * 1000.0)
            latencies.sort()
            lat = {
                "p50_ms": round(_percentile(latencies, 50), 2),
                "p95_ms": round(_percentile(latencies, 95), 2),
                "p99_ms": round(_percentile(latencies, 99), 2),
                "mean_ms": round(statistics.mean(latencies), 2),
            }
        elif name == "TF-IDF":
            metrics = evaluate_system(name, retr.search, auto_queries)
            latencies = []
            for query in auto_queries[:50]:
                t0 = time.perf_counter()
                retr.search(query.query_text, top_k=5)
                latencies.append((time.perf_counter() - t0) * 1000.0)
            latencies.sort()
            lat = {
                "p50_ms": round(_percentile(latencies, 50), 2),
                "p95_ms": round(_percentile(latencies, 95), 2),
                "p99_ms": round(_percentile(latencies, 99), 2),
                "mean_ms": round(statistics.mean(latencies), 2),
            }
        elif hasattr(retr, 'search_with_latency'):
            def dense_fn(query_text, top_k=5, _retr=retr):
                return _retr.search(query_text, top_k=top_k)
            metrics = evaluate_system(name, dense_fn, auto_queries)
            lat = latency_benchmark(name, retr)
        else:
            def hybrid_fn(query_text, top_k=5, _retr=retr):
                return _retr.search(query_text, top_k=top_k)
            metrics = evaluate_system(name, hybrid_fn, auto_queries)
            latencies = []
            for query in auto_queries[:50]:
                t0 = time.perf_counter()
                retr.search(query.query_text, top_k=5)
                latencies.append((time.perf_counter() - t0) * 1000.0)
            latencies.sort()
            lat = {
                "p50_ms": round(_percentile(latencies, 50), 2),
                "p95_ms": round(_percentile(latencies, 95), 2),
                "p99_ms": round(_percentile(latencies, 99), 2),
                "mean_ms": round(statistics.mean(latencies), 2),
            }

        results["systems"][name] = {
            "auto_generated": metrics,
            "latency_ms": lat,
        }
        print(f"  R@5={metrics.get('recall@5', 0):.4f} "
              f"P@5={metrics.get('precision@5', 0):.4f} "
              f"MRR={metrics.get('mrr', 0):.4f} "
              f"nDCG@5={metrics.get('ndcg@5', 0):.4f} "
              f"| p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms", flush=True)

    # Evaluate on human-validated labels
    if human_queries:
        print("\n--- Human-validated evaluation ---", flush=True)
        for name in ["Dense (MPNet 768d)", "Hybrid (weighted fusion)", "BM25"]:
            retr = retrievers[name]
            if name == "BM25":
                def bm25_fn(query_text, top_k=5):
                    docs = bm25_index.search(query_text, top_k=top_k * 2)
                    idxs = []
                    for d in docs:
                        key = _case_to_index_key(d)
                        i = retrievers["TF-IDF"].case_to_index.get(key)
                        if i is not None:
                            idxs.append(str(i))
                    return idxs[:top_k]
                metrics = evaluate_system(name, bm25_fn, human_queries)
            else:
                def std_fn(query_text, top_k=5, _retr=retr):
                    return _retr.search(query_text, top_k=top_k)
                metrics = evaluate_system(name, std_fn, human_queries)
            results["systems"][name]["human_validated"] = metrics
            print(f"  {name}: R@5={metrics.get('recall@5', 0):.4f} "
                  f"P@5={metrics.get('precision@5', 0):.4f} "
                  f"MRR={metrics.get('mrr', 0):.4f}", flush=True)

    # Write results
    out_path = EXPERIMENT_DIR / "phase2_benchmark.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}", flush=True)
    return results


if __name__ == "__main__":
    run_benchmark()
