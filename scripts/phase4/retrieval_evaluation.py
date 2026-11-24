"""
NyayaSaathi Phase 4 — Retrieval Evaluation Pipeline.

Compares multiple retrieval systems on validated (human-annotated) and
auto-generated evaluation datasets with proper metrics and confidence intervals.

Usage:
    python retrieval_evaluation.py
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from api.data_loader import CASES
from api.nlp.bm25_index import BM25Index
from api.search_engine import simple_search

import re

HINGLISH_NORMALIZATION = {
    "kabja": "encroachment", "kabza": "encroachment", "zameen": "land",
    "jameen": "land", "dhokha": "fraud", "cheated": "fraud",
    "fraud hua": "scammed", "thagi": "scam", "thana": "police station",
    "marpeet": "assault", "dahej": "dowry", "talaq": "divorce",
    "salary nahi mila": "salary not paid", "job se nikal diya": "wrongful termination",
    "salary nahi di": "salary not paid", "nahi mila": "not paid",
    "not received": "not paid", "cyber thagi": "cyber fraud", "upi fraud": "upi scam",
}

SYNONYM_MAP = {
    "occupy": ["encroachment", "illegal occupation"],
    "occupied": ["encroachment", "illegal occupation"],
    "scammed": ["fraud", "cyber fraud"], "scam": ["fraud", "cyber fraud"],
    "fraud": ["cheating", "cyber fraud"], "not": ["unpaid"],
    "paid": ["salary issue"], "employer": ["company", "boss"],
    "company": ["employer", "boss"], "unpaid": ["salary issue", "salary dispute"],
    "land": ["property", "land dispute"], "threat": ["intimidation", "criminal threat"],
    "beaten": ["assault", "physical violence"], "salary": ["wage", "labour", "salary dispute", "salary non-payment"],
    "fired": ["termination", "wrongful termination"], "upi": ["digital payment", "cyber fraud"],
}

STOPWORDS = {
    "a", "an", "the", "is", "are", "to", "for", "of", "in", "on",
    "through", "my", "me", "meri", "mera", "mujhe", "par", "ko", "ne",
    "ki", "ka", "ke", "ho", "gaya", "hai", "someone",
}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    for src in sorted(HINGLISH_NORMALIZATION.keys(), key=len, reverse=True):
        target = HINGLISH_NORMALIZATION[src]
        text = re.sub(rf"\b{re.escape(src)}\b", target, text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

BACKEND = Path(__file__).resolve().parent.parent.parent
EXPERIMENT_DIR = BACKEND / "backend" / "evaluation" / "phase4"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
N_BOOTSTRAP = 2000


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def _case_content_key(case: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(case.get("category", "")).strip().lower(),
        str(case.get("subcategory", "")).strip().lower(),
        str(case.get("problem_description", "")).strip().lower(),
    )


def build_deduped_corpus(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for case in cases:
        key = _case_content_key(case)
        if key not in seen:
            seen.add(key)
            unique.append(case)
    return unique


def case_to_searchable_text(case: dict[str, Any]) -> str:
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


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_candidate_queries() -> list[dict[str, Any]]:
    path = EXPERIMENT_DIR / "annotations" / "candidate_queries.jsonl"
    if not path.exists():
        return []
    queries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


def load_validated_queries() -> list[dict[str, Any]]:
    path = EXPERIMENT_DIR / "annotations" / "validated_dataset.jsonl"
    if not path.exists():
        return []
    queries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


def load_split_queries(split: str) -> list[dict[str, Any]]:
    path = EXPERIMENT_DIR / "splits" / f"{split}.jsonl"
    if not path.exists():
        return []
    queries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))
    return queries


# ---------------------------------------------------------------------------
# Retrieval systems
# ---------------------------------------------------------------------------

class DenseRetriever:
    def __init__(self, model_name: str, cases: list[dict[str, Any]]):
        self.model_name = model_name
        self.cases = cases
        self.case_to_index = {
            _case_content_key(c): i for i, c in enumerate(cases)
        }
        self.model = SentenceTransformer(model_name)
        self.dim = int(self.model.get_embedding_dimension())
        self._is_e5 = "e5" in model_name.lower()
        self._build_index()

    def _build_index(self):
        texts = [case_to_searchable_text(c) for c in self.cases]
        if self._is_e5:
            texts = ["passage: " + t for t in texts]
        vecs = self.model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True,
            batch_size=32, show_progress_bar=False,
        )
        self.embeddings = np.asarray(vecs, dtype="float32")
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(self.embeddings)

    def _encode_query(self, query: str, use_normalization: bool = False) -> np.ndarray:
        if use_normalization:
            query = normalize_text(query)
        qtext = "query: " + query if self._is_e5 else query
        qv = self.model.encode(
            [qtext], convert_to_numpy=True, normalize_embeddings=True,
        )
        return np.asarray(qv, dtype="float32")[0]

    def search(self, query: str, top_k: int = 5, use_normalization: bool = False) -> list[str]:
        qv = self._encode_query(query, use_normalization=use_normalization)
        k = min(top_k, len(self.cases))
        scores, indices = self.index.search(qv.reshape(1, -1), k)
        return [
            str(int(indices[0][i]))
            for i in range(len(indices[0]))
            if 0 <= int(indices[0][i]) < len(self.cases)
        ]


class BM25Retriever:
    def __init__(self, cases: list[dict[str, Any]]):
        self.cases = cases
        self.case_to_index = {
            _case_content_key(c): i for i, c in enumerate(cases)
        }
        self.index = BM25Index(cases)

    def search(self, query: str, top_k: int = 5, use_normalization: bool = False) -> list[str]:
        if use_normalization:
            query = normalize_text(query)
        docs = self.index.search(query, top_k=top_k * 2)
        indices = []
        for doc in docs:
            key = _case_content_key(doc)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]


class TFIDFRetriever:
    def __init__(self, cases: list[dict[str, Any]]):
        self.cases = cases
        self.case_to_index = {
            _case_content_key(c): i for i, c in enumerate(cases)
        }

    def search(self, query: str, top_k: int = 5, use_normalization: bool = False) -> list[str]:
        if use_normalization:
            query = normalize_text(query)
        results = simple_search(query)
        indices = []
        for case in results:
            key = _case_content_key(case)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def recall_at_k(ranked_relevant: list[bool], k: int, n_relevant: int) -> float:
    if n_relevant == 0:
        return 0.0
    return float(sum(ranked_relevant[:k]) / n_relevant)


def precision_at_k(ranked_relevant: list[bool], k: int) -> float:
    if k == 0:
        return 0.0
    return float(sum(ranked_relevant[:k]) / k)


def mrr(ranked_relevant: list[bool]) -> float:
    for i, rel in enumerate(ranked_relevant, start=1):
        if rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_relevant: list[bool], k: int, n_relevant: int) -> float:
    if n_relevant == 0:
        return 0.0
    dcg = 0.0
    for i, rel in enumerate(ranked_relevant[:k], start=1):
        if rel:
            dcg += 1.0 / math.log2(i + 1)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(n_relevant, k) + 1))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def average_precision(ranked_relevant: list[bool], n_relevant: int) -> float:
    if n_relevant == 0:
        return 0.0
    hits = 0
    sum_precision = 0.0
    for i, rel in enumerate(ranked_relevant, start=1):
        if rel:
            hits += 1
            sum_precision += hits / i
    return sum_precision / n_relevant


def hit_rate_at_k(ranked_relevant: list[bool], k: int) -> float:
    return 1.0 if any(ranked_relevant[:k]) else 0.0


def _percentile(sorted_vals: list[float], p: float) -> float:
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


def _ci95(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        v = float(values[0]) if values else 0.0
        return (v, v)
    rng = np.random.RandomState(RANDOM_SEED)
    boot_means = []
    n = len(values)
    for _ in range(N_BOOTSTRAP):
        sample = rng.choice(values, size=n, replace=True)
        boot_means.append(float(np.mean(sample)))
    boot_means.sort()
    lo = _percentile(boot_means, 2.5)
    hi = _percentile(boot_means, 97.5)
    return (lo, hi)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_single_query(
    query: dict[str, Any],
    retrieved_ids: list[str],
    k_values: list[int] = None,
) -> dict[str, Any]:
    if k_values is None:
        k_values = [1, 3, 5, 10]

    relevant_ids = set(query.get("relevant_case_ids", []))
    n_relevant = len(relevant_ids)
    relevance_grades = query.get("relevance_grades", {})

    ranked_relevant = [cid in relevant_ids for cid in retrieved_ids]

    metrics = {}
    for k in k_values:
        metrics[f"recall@{k}"] = recall_at_k(ranked_relevant, k, n_relevant)
        metrics[f"precision@{k}"] = precision_at_k(ranked_relevant, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(ranked_relevant, k, n_relevant)
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(ranked_relevant, k)
    metrics["mrr"] = mrr(ranked_relevant)
    metrics["map"] = average_precision(ranked_relevant, n_relevant)
    metrics["n_relevant"] = n_relevant

    # Graded nDCG (if relevance grades available)
    if relevance_grades:
        for k in k_values:
            dcg = 0.0
            for i, rel in enumerate(ranked_relevant[:k], start=1):
                if rel:
                    grade = relevance_grades.get(retrieved_ids[i - 1], 0)
                    dcg += (2 ** grade - 1) / math.log2(i + 1)
            idcg = sum(
                (2 ** relevance_grades.get(retrieved_ids[i], 0) - 1) / math.log2(i + 2)
                for i in range(min(len(retrieved_ids), k))
            )
            metrics[f"graded_ndcg@{k}"] = dcg / idcg if idcg > 0 else 0.0

    return metrics


def evaluate_system(
    name: str,
    retrieve_fn,
    queries: list[dict[str, Any]],
) -> dict[str, Any]:
    per_query = []
    latencies = []

    for query in queries:
        t0 = time.perf_counter()
        retrieved = retrieve_fn(query["query_text"], top_k=10)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)

        metrics = evaluate_single_query(query, retrieved)
        per_query.append({
            "query_id": query["query_id"],
            "query_text": query["query_text"],
            "category": query.get("category", ""),
            "difficulty": query.get("difficulty", ""),
            "retrieved_ids": retrieved,
            "metrics": metrics,
            "latency_ms": latency_ms,
        })

    # Aggregate
    n = len(per_query)
    if n == 0:
        return {"n_queries": 0, "metrics": {}, "latency_ms": {}}

    metric_keys = set()
    for pq in per_query:
        metric_keys.update(pq["metrics"].keys())

    agg_metrics: dict[str, Any] = {}
    for key in metric_keys:
        values = [pq["metrics"][key] for pq in per_query if key in pq["metrics"]]
        if values:
            ci_lo, ci_hi = _ci95(values)
            agg_metrics[key] = round(float(np.mean(values)), 4)
            agg_metrics[f"{key}_ci_lo"] = round(ci_lo, 4)
            agg_metrics[f"{key}_ci_hi"] = round(ci_hi, 4)

    latencies.sort()
    latency_stats = {
        "p50_ms": round(_percentile(latencies, 50), 2),
        "p95_ms": round(_percentile(latencies, 95), 2),
        "p99_ms": round(_percentile(latencies, 99), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
    }

    return {
        "n_queries": n,
        "metrics": agg_metrics,
        "latency_ms": latency_stats,
        "per_query": per_query,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("NyayaSaathi Phase 4 — Retrieval Evaluation Pipeline")
    print("=" * 70)

    # Load deduped corpus
    deduped_cases = build_deduped_corpus(CASES)
    print(f"Loaded {len(deduped_cases)} deduplicated cases")

    # Load datasets
    candidate_queries = load_candidate_queries()
    validated_queries = load_validated_queries()
    test_queries = load_split_queries("test")

    print(f"Candidate queries: {len(candidate_queries)}")
    print(f"Validated queries: {len(validated_queries)}")
    print(f"Test split queries: {len(test_queries)}")

    # Determine which dataset to use for evaluation
    # Priority: test split > validated > candidate (auto-generated labels only)
    if test_queries:
        eval_queries = test_queries
        label_source = "human-validated (test split)"
    elif validated_queries:
        eval_queries = validated_queries
        label_source = "human-validated"
    else:
        # Fall back to candidate queries with auto-generated labels
        # Build auto labels: same subcategory = relevant
        eval_queries = []
        for q in candidate_queries:
            subcat = q.get("subcategory", "")
            matching = [
                str(i) for i, c in enumerate(deduped_cases)
                if str(c.get("subcategory", "")).strip().lower()
                == subcat.strip().lower()
            ]
            eval_queries.append({
                "query_id": q["query_id"],
                "query_text": q["query_text"],
                "language": q.get("language", "en"),
                "category": q.get("category", ""),
                "subcategory": q.get("subcategory", ""),
                "difficulty": q.get("difficulty", "medium"),
                "source": q.get("source", "seed"),
                "relevant_case_ids": matching,
                "relevance_grades": {},
                "label_source": "auto-generated (category proxy)",
            })
        label_source = "auto-generated (category proxy)"
        print(
            f"WARNING: No validated queries found. Using {len(eval_queries)} "
            "auto-generated category-proxy labels. These are NOT human judgments."
        )

    print(f"Evaluation queries: {len(eval_queries)}")
    print(f"Label source: {label_source}")

    # Initialize retrievers
    print("\nInitializing retrievers...", flush=True)
    dense_models = {
        "MiniLM (384d)": "sentence-transformers/all-MiniLM-L6-v2",
        "MPNet (768d)": "sentence-transformers/all-mpnet-base-v2",
        "E5-base (768d)": "intfloat/e5-base-v2",
        "BGE-base (768d)": "BAAI/bge-base-en-v1.5",
    }

    dense_retrievers: dict[str, DenseRetriever] = {}
    for label, model_name in dense_models.items():
        print(f"  Loading {label} ...", flush=True)
        dense_retrievers[label] = DenseRetriever(model_name, deduped_cases)

    bm25_retriever = BM25Retriever(deduped_cases)
    tfidf_retriever = TFIDFRetriever(deduped_cases)

    # Define experiment configurations
    experiments: list[tuple[str, Any]] = [
        ("TF-IDF (baseline)", tfidf_retriever.search),
        ("BM25 (baseline)", bm25_retriever.search),
    ]
    for label, retr in dense_retrievers.items():
        experiments.append((f"{label} (baseline)", retr.search))
        experiments.append((
            f"{label} + normalization",
            lambda q, top_k=5, _retr=retr: _retr.search(q, top_k=top_k, use_normalization=True),
        ))

    # Run experiments
    results: dict[str, Any] = {
        "n_deduped_cases": len(deduped_cases),
        "n_eval_queries": len(eval_queries),
        "label_source": label_source,
        "random_seed": RANDOM_SEED,
        "experiments": {},
    }

    for name, retrieve_fn in experiments:
        print(f"\n  {name} ...", flush=True)
        result = evaluate_system(name, retrieve_fn, eval_queries)
        results["experiments"][name] = {
            "label_source": label_source,
            "n_queries": result["n_queries"],
            "metrics": result["metrics"],
            "latency_ms": result["latency_ms"],
        }
        m = result["metrics"]
        lat = result["latency_ms"]
        print(
            f"    R@5={m.get('recall@5', 0):.4f} "
            f"CI=[{m.get('recall@5_ci_lo', 0):.4f}, {m.get('recall@5_ci_hi', 0):.4f}] "
            f"P@5={m.get('precision@5', 0):.4f} "
            f"MRR={m.get('mrr', 0):.4f} "
            f"nDCG@5={m.get('ndcg@5', 0):.4f} "
            f"MAP={m.get('map', 0):.4f} "
            f"| p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms",
            flush=True,
        )

    # Write results
    out_path = EXPERIMENT_DIR / "retrieval_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")

    # Print comparison table
    print("\n" + "=" * 70)
    print("COMPARISON — Recall@5 with 95% CI")
    print("=" * 70)
    for name, exp in results["experiments"].items():
        m = exp["metrics"]
        print(
            f"  {name:<35s} R@5={m.get('recall@5', 0):.4f} "
            f"CI=[{m.get('recall@5_ci_lo', 0):.4f}, {m.get('recall@5_ci_hi', 0):.4f}] "
            f"P@5={m.get('precision@5', 0):.4f} "
            f"MRR={m.get('mrr', 0):.4f} "
            f"nDCG@5={m.get('ndcg@5', 0):.4f} "
            f"MAP={m.get('map', 0):.4f}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())