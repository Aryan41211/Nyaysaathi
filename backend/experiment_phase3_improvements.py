"""NyaySaathi Phase 3 — Retrieval Improvement Experiments.

Tests the highest-impact improvements on top of the Phase 2.5 baseline:
1. Query normalization (Hinglish + domain synonyms) on dense retrieval
2. Multi-query retrieval with RRF fusion
3. Hybrid retrieval (BM25 + dense) with RRF and weighted fusion
4. Cross-encoder reranking (when available)

Evaluates on both auto-generated (category proxy) and human-validated labels.
Saves machine-readable results with confidence intervals.

Usage:
    python experiment_phase3_improvements.py
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from api.nlp.semantic_engine import get_semantic_engine, SemanticSearchEngine
from api.nlp.bm25_index import BM25Index
from api.nlp.hybrid_retrieval import HybridRetriever, _rrf_rank, _case_content_key
from api.nlp.query_processor import (
    normalize_text,
    tokenize,
    expand_synonyms,
    expand_phrase_synonyms,
    expand_query_variants,
    ENHANCED_HINGLISH,
    ENHANCED_SYNONYMS,
)
from api.nlp.cross_encoder_reranker import CrossEncoderReranker
from api.search_engine import simple_search
from evaluation import EvalQuery, evaluate_single_query, aggregate
from evaluation.dataset import build_auto_generated_dataset

BACKEND = Path(__file__).resolve().parent
EXPERIMENT_DIR = BACKEND / "experiment_results"
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Corpus loading (deduplicated 232-case corpus from semantic engine)
# ---------------------------------------------------------------------------


def _case_to_index_key(case: Dict[str, Any]) -> tuple:
    return (
        str(case.get("category", "")).strip().lower(),
        str(case.get("subcategory", "")).strip().lower(),
        str(case.get("problem_description", "")).strip().lower(),
    )


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


def load_deduped_cases() -> List[Dict[str, Any]]:
    engine = get_semantic_engine()
    engine.ensure_ready()
    return engine.get_cases()


def load_expanded_cases() -> List[Dict[str, Any]]:
    path = BACKEND / "dataset" / "expanded_cases.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_expanded_to_deduped_map(
    expanded_cases: List[Dict[str, Any]],
    deduped_cases: List[Dict[str, Any]],
) -> Dict[int, int]:
    """Map expanded case index -> deduped case index by content key."""
    deduped_keys = {_case_to_index_key(c): i for i, c in enumerate(deduped_cases)}
    mapping: Dict[int, int] = {}
    for orig_idx, case in enumerate(expanded_cases):
        key = _case_to_index_key(case)
        if key in deduped_keys:
            mapping[orig_idx] = deduped_keys[key]
    return mapping


# ---------------------------------------------------------------------------
# Human-validated dataset loading with proper dedup mapping
# ---------------------------------------------------------------------------


def load_human_validated_dataset(
    expanded_to_deduped: Dict[int, int],
) -> List[EvalQuery]:
    path = BACKEND / "evaluation" / "datasets" / "human_validated.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    queries: List[EvalQuery] = []
    for item in data.get("queries", []):
        mapped_ids = []
        for cid_str in item.get("relevant_case_ids", []):
            orig_idx = int(cid_str)
            if orig_idx in expanded_to_deduped:
                mapped_ids.append(str(expanded_to_deduped[orig_idx]))
        if mapped_ids:
            queries.append(
                EvalQuery(
                    query_id=item["query_id"],
                    query_text=item["query_text"],
                    relevant_case_ids=mapped_ids,
                    relevance_grades=item.get("relevance_grades", {}),
                    label_source="human-validated",
                    metadata=item.get("metadata", {}),
                )
            )
    return queries


# ---------------------------------------------------------------------------
# Retrieval system implementations
# ---------------------------------------------------------------------------


class DenseRetriever:
    """Dense retriever backed by a sentence-transformers model."""

    def __init__(self, model_name: str, cases: List[Dict[str, Any]]):
        self.model_name = model_name
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }
        self.model = SentenceTransformer(model_name)
        self.dim = int(self.model.get_embedding_dimension())
        self._is_e5 = "e5" in model_name.lower()
        self._build_index()

    def _build_index(self):
        texts = [_build_searchable_text(c) for c in self.cases]
        if self._is_e5:
            texts = ["passage: " + t for t in texts]
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

    def _encode_query(self, query: str, use_normalization: bool = False) -> np.ndarray:
        if use_normalization:
            query = normalize_text(query)
        qtext = "query: " + query if self._is_e5 else query
        qv = self.model.encode(
            [qtext], convert_to_numpy=True, normalize_embeddings=True
        )
        return np.asarray(qv, dtype="float32")[0]

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_normalization: bool = False,
    ) -> List[str]:
        qv = self._encode_query(query, use_normalization=use_normalization)
        k = min(top_k, len(self.cases))
        scores, indices = self.index.search(qv.reshape(1, -1), k)
        return [
            str(int(indices[0][i]))
            for i in range(len(indices[0]))
            if 0 <= int(indices[0][i]) < len(self.cases)
        ]

    def search_multi_query(
        self,
        query: str,
        top_k: int = 5,
        use_normalization: bool = False,
        max_variants: int = 5,
    ) -> List[str]:
        """Multi-query retrieval: generate variants, retrieve for each, fuse with RRF."""
        variants = expand_query_variants(query, max_variants=max_variants)
        all_ranked: List[List[str]] = []
        for variant in variants:
            ids = self.search(variant, top_k=top_k * 2, use_normalization=use_normalization)
            all_ranked.append(ids)

        # RRF fusion across variants
        scores: Dict[str, float] = {}
        k_rrf = 60
        for ranked_list in all_ranked:
            for rank, doc_id in enumerate(ranked_list, start=1):
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k_rrf + rank)

        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in fused[:top_k]]


class BM25Retriever:
    """Pure BM25 sparse retriever."""

    def __init__(self, cases: List[Dict[str, Any]]):
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }
        self.index = BM25Index(cases)

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_normalization: bool = False,
    ) -> List[str]:
        if use_normalization:
            query = normalize_text(query)
        docs = self.index.search(query, top_k=top_k * 2)
        indices = []
        for doc in docs:
            key = _case_to_index_key(doc)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]


class TFIDFRetriever:
    """TF-IDF lexical retriever via simple_search."""

    def __init__(self, cases: List[Dict[str, Any]]):
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_normalization: bool = False,
    ) -> List[str]:
        if use_normalization:
            query = normalize_text(query)
        results = simple_search(query)
        indices = []
        for case in results:
            key = _case_to_index_key(case)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]


class HybridRetrieverWrapper:
    """Hybrid retrieval: BM25 + dense with RRF or weighted fusion."""

    def __init__(
        self,
        cases: List[Dict[str, Any]],
        dense_model_name: str = "sentence-transformers/all-mpnet-base-v2",
        fusion: str = "rrf",
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
        use_normalization: bool = False,
    ):
        self.cases = cases
        self.case_to_index = {
            _case_to_index_key(c): i for i, c in enumerate(cases)
        }
        self.fusion = fusion
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
        self.use_normalization = use_normalization

        self.dense = DenseRetriever(dense_model_name, cases)
        self.bm25 = BM25Index(cases)

    def _tfidf_results(self, query: str) -> List[Dict[str, Any]]:
        results = simple_search(query)
        return [{"case": c, "source": "tfidf", "raw_score": 1.0} for c in results]

    def _bm25_results(self, query: str) -> List[Dict[str, Any]]:
        docs = self.bm25.search(query, top_k=20)
        return [{"case": doc, "source": "bm25", "raw_score": float(doc.get("bm25_score", 0.0))} for doc in docs]

    def _dense_results(self, query: str) -> List[Dict[str, Any]]:
        hits = self.dense.search(query, top_k=20, use_normalization=self.use_normalization)
        return [
            {"case": self.cases[int(hit)], "source": "dense", "raw_score": 1.0}
            for hit in hits
        ]

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[str]:
        if not query or not query.strip():
            return []

        q = normalize_text(query) if self.use_normalization else query

        tfidf = self._tfidf_results(q)
        bm25 = self._bm25_results(q)
        dense = self._dense_results(q)

        system_results: Dict[str, List[Dict[str, Any]]] = {}
        if tfidf:
            system_results["tfidf"] = tfidf
        if bm25:
            system_results["bm25"] = bm25
        if dense:
            system_results["dense"] = dense

        if not system_results:
            return []

        if self.fusion == "rrf":
            lists = [system_results[s] for s in system_results]
            fused = _rrf_rank(lists, k=60)
        else:
            # Weighted fusion with content-key matching
            from api.nlp.hybrid_retrieval import _weighted_fuse
            fused = _weighted_fuse(
                system_results,
                {"tfidf": 0.1, "bm25": self.bm25_weight, "dense": self.dense_weight},
                score_key="raw_score",
            )

        indices = []
        for item in fused[:top_k]:
            case = item.get("case", item)
            key = _case_content_key(case)
            idx = self.case_to_index.get(key)
            if idx is not None:
                indices.append(str(idx))
        return indices[:top_k]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


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


def _ci95(values: List[float]) -> Tuple[float, float]:
    """95% confidence interval using bootstrap."""
    if len(values) < 2:
        return (float(values[0]) if values else 0.0, float(values[0]) if values else 0.0)
    n_bootstrap = 2000
    rng = np.random.RandomState(42)
    boot_means = []
    n = len(values)
    for _ in range(n_bootstrap):
        sample = rng.choice(values, size=n, replace=True)
        boot_means.append(float(np.mean(sample)))
    boot_means.sort()
    lo = _percentile(boot_means, 2.5)
    hi = _percentile(boot_means, 97.5)
    return (lo, hi)


def evaluate_system(
    name: str,
    retrieve_fn: Callable[[str, int], List[str]],
    queries: List[EvalQuery],
) -> Dict[str, Any]:
    """Evaluate a retrieval system on a set of queries. Returns per-query metrics and aggregates."""
    per_query = []
    for query in queries:
        retrieved = retrieve_fn(query.query_text, top_k=10)
        result = evaluate_single_query(query, retrieved)
        per_query.append(result)

    report = aggregate(per_query, name, queries[0].label_source if queries else "unknown")

    # Per-query recall@5 values for CI
    r5_values = [r.recall_at_k[5] for r in per_query]
    ci_lo, ci_hi = _ci95(r5_values)

    return {
        "metrics": report.metrics,
        "n_queries": len(per_query),
        "recall_at_5_ci95": {"lo": ci_lo, "hi": ci_hi},
        "per_query_recall_at_5": r5_values,
    }


def latency_benchmark(
    name: str,
    retrieve_fn: Callable[[str, int], List[str]],
    test_queries: List[str],
    n_runs: int = 3,
) -> Dict[str, float]:
    """Measure p50/p95/p99 latency over multiple runs."""
    latencies: List[float] = []
    for _ in range(n_runs):
        for query in test_queries:
            t0 = time.perf_counter()
            retrieve_fn(query, top_k=5)
            latencies.append((time.perf_counter() - t0) * 1000.0)
    latencies.sort()
    return {
        "p50_ms": round(_percentile(latencies, 50), 2),
        "p95_ms": round(_percentile(latencies, 95), 2),
        "p99_ms": round(_percentile(latencies, 99), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
    }


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 70)
    print("NyayaSaathi Phase 3 — Retrieval Improvement Experiments")
    print("=" * 70)

    # Load corpus
    deduped_cases = load_deduped_cases()
    print(f"Loaded {len(deduped_cases)} deduplicated cases")

    expanded_cases = load_expanded_cases()
    expanded_to_deduped = build_expanded_to_deduped_map(expanded_cases, deduped_cases)
    print(f"Expanded-to-deduped mapping: {len(expanded_to_deduped)} of {len(expanded_cases)} expanded cases map")

    # Build datasets
    auto_queries = build_auto_generated_dataset(deduped_cases)
    print(f"Auto-generated queries: {len(auto_queries)}")

    human_queries = load_human_validated_dataset(expanded_to_deduped)
    print(f"Human-validated queries (mapped): {len(human_queries)}")

    # Report how many relevant cases per human query survive dedup mapping
    human_rel_counts = [len(q.relevant_case_ids) for q in human_queries]
    if human_rel_counts:
        print(
            f"Human-validated relevant cases per query: min={min(human_rel_counts)}, "
            f"max={max(human_rel_counts)}, mean={statistics.mean(human_rel_counts):.1f}"
        )

    # Test queries for latency
    test_queries = [q.query_text for q in auto_queries[:50]]

    # ------------------------------------------------------------------
    # Initialize retrievers
    # ------------------------------------------------------------------
    print("\nInitializing retrievers...")
    dense_models = {
        "MiniLM (384d)": "sentence-transformers/all-MiniLM-L6-v2",
        "MPNet (768d)": "sentence-transformers/all-mpnet-base-v2",
        "E5-base (768d)": "intfloat/e5-base-v2",
        "BGE-base (768d)": "BAAI/bge-base-en-v1.5",
    }

    dense_retrievers: Dict[str, DenseRetriever] = {}
    for label, model_name in dense_models.items():
        print(f"  Loading {label} ...", flush=True)
        dense_retrievers[label] = DenseRetriever(model_name, deduped_cases)

    bm25_retriever = BM25Retriever(deduped_cases)
    tfidf_retriever = TFIDFRetriever(deduped_cases)

    # Hybrid retrievers
    hybrid_rrf_mpnet = HybridRetrieverWrapper(
        deduped_cases,
        dense_model_name="sentence-transformers/all-mpnet-base-v2",
        fusion="rrf",
        use_normalization=False,
    )
    hybrid_weighted_mpnet = HybridRetrieverWrapper(
        deduped_cases,
        dense_model_name="sentence-transformers/all-mpnet-base-v2",
        fusion="weighted",
        use_normalization=False,
    )
    hybrid_rrf_mpnet_norm = HybridRetrieverWrapper(
        deduped_cases,
        dense_model_name="sentence-transformers/all-mpnet-base-v2",
        fusion="rrf",
        use_normalization=True,
    )

    # Cross-encoder reranker (optional)
    reranker = None
    try:
        reranker = CrossEncoderReranker()
        if reranker._load_model():
            print(f"  Cross-encoder loaded: {reranker.model_name}")
        else:
            print(f"  Cross-encoder not available: {reranker._model_error}")
            reranker = None
    except Exception as exc:
        print(f"  Cross-encoder not available: {exc}")
        reranker = None

    # ------------------------------------------------------------------
    # Define experiment configurations
    # ------------------------------------------------------------------
    experiments: List[Tuple[str, Callable[[str, int], List[str]]]] = []

    # Baseline: individual retrievers (no normalization)
    experiments.append(("BM25 (baseline)", bm25_retriever.search))
    experiments.append(("TF-IDF (baseline)", tfidf_retriever.search))
    for label, retr in dense_retrievers.items():
        experiments.append((f"{label} (baseline)", retr.search))

    # Dense with normalization
    for label, retr in dense_retrievers.items():
        experiments.append((
            f"{label} + normalization",
            lambda q, top_k=5, _retr=retr: _retr.search(q, top_k=top_k, use_normalization=True),
        ))

    # Dense + multi-query (RRF fusion across variants)
    for label, retr in dense_retrievers.items():
        experiments.append((
            f"{label} + multi-query (RRF)",
            lambda q, top_k=5, _retr=retr: _retr.search_multi_query(q, top_k=top_k, use_normalization=False),
        ))

    # Dense + normalization + multi-query
    for label, retr in dense_retrievers.items():
        experiments.append((
            f"{label} + normalization + multi-query",
            lambda q, top_k=5, _retr=retr: _retr.search_multi_query(
                q, top_k=top_k, use_normalization=True,
            ),
        ))

    # Hybrid retrieval
    experiments.append(("Hybrid BM25+MPNet (RRF)", hybrid_rrf_mpnet.search))
    experiments.append(("Hybrid BM25+MPNet (weighted)", hybrid_weighted_mpnet.search))
    experiments.append(("Hybrid BM25+MPNet (RRF + norm)", hybrid_rrf_mpnet_norm.search))

    # ------------------------------------------------------------------
    # Run experiments on auto-generated labels
    # ------------------------------------------------------------------
    results: Dict[str, Any] = {
        "n_deduped_cases": len(deduped_cases),
        "n_auto_queries": len(auto_queries),
        "n_human_queries": len(human_queries),
        "n_expanded_cases": len(expanded_cases),
        "n_expanded_to_deduped_mapped": len(expanded_to_deduped),
        "experiments": {},
    }

    print("\n" + "=" * 70)
    print("Running experiments on AUTO-GENERATED labels")
    print("=" * 70)

    for name, retrieve_fn in experiments:
        print(f"\n  {name} ...", flush=True)
        t0 = time.perf_counter()
        eval_result = evaluate_system(name, retrieve_fn, auto_queries)
        eval_sec = time.perf_counter() - t0

        # Latency
        lat = latency_benchmark(name, retrieve_fn, test_queries)

        results["experiments"][name] = {
            "label_source": "auto-generated",
            "eval_sec": round(eval_sec, 2),
            "metrics": eval_result["metrics"],
            "recall_at_5_ci95": eval_result["recall_at_5_ci95"],
            "n_queries": eval_result["n_queries"],
            "latency_ms": lat,
        }
        m = eval_result["metrics"]
        print(
            f"    R@5={m.get('recall@5', 0):.4f} "
            f"P@5={m.get('precision@5', 0):.4f} "
            f"MRR={m.get('mrr', 0):.4f} "
            f"nDCG@5={m.get('ndcg@5', 0):.4f} "
            f"| CI95=[{eval_result['recall_at_5_ci95']['lo']:.4f}, {eval_result['recall_at_5_ci95']['hi']:.4f}] "
            f"| p50={lat['p50_ms']}ms p95={lat['p95_ms']}ms",
            flush=True,
        )

    # ------------------------------------------------------------------
    # Run experiments on human-validated labels
    # ------------------------------------------------------------------
    if human_queries:
        print("\n" + "=" * 70)
        print("Running experiments on HUMAN-VALIDATED labels")
        print("=" * 70)

        for name, retrieve_fn in experiments:
            print(f"\n  {name} ...", flush=True)
            t0 = time.perf_counter()
            eval_result = evaluate_system(name, retrieve_fn, human_queries)
            eval_sec = time.perf_counter() - t0

            lat = latency_benchmark(name, retrieve_fn, test_queries)

            if "human_validated" not in results["experiments"][name]:
                results["experiments"][name]["human_validated"] = {}

            results["experiments"][name]["human_validated"] = {
                "eval_sec": round(eval_sec, 2),
                "metrics": eval_result["metrics"],
                "recall_at_5_ci95": eval_result["recall_at_5_ci95"],
                "n_queries": eval_result["n_queries"],
                "latency_ms": lat,
            }
            m = eval_result["metrics"]
            print(
                f"    R@5={m.get('recall@5', 0):.4f} "
                f"P@5={m.get('precision@5', 0):.4f} "
                f"MRR={m.get('mrr', 0):.4f} "
                f"| CI95=[{eval_result['recall_at_5_ci95']['lo']:.4f}, {eval_result['recall_at_5_ci95']['hi']:.4f}]",
                flush=True,
            )

    # ------------------------------------------------------------------
    # Write results
    # ------------------------------------------------------------------
    out_path = EXPERIMENT_DIR / "phase3_improvements.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY — Auto-Generated Labels (Recall@5 with 95% CI)")
    print("=" * 70)
    for name, exp in results["experiments"].items():
        if "auto_generated" in exp:
            m = exp["auto_generated"]["metrics"]
            ci = exp["auto_generated"]["recall_at_5_ci95"]
            print(
                f"  {name:45s} R@5={m.get('recall@5', 0):.4f} "
                f"CI95=[{ci['lo']:.4f}, {ci['hi']:.4f}] "
                f"p50={exp['auto_generated']['latency_ms']['p50_ms']}ms"
            )

    print("\n" + "=" * 70)
    print("SUMMARY — Human-Validated Labels (Recall@5 with 95% CI)")
    print("=" * 70)
    for name, exp in results["experiments"].items():
        if "human_validated" in exp:
            m = exp["human_validated"]["metrics"]
            ci = exp["human_validated"]["recall_at_5_ci95"]
            print(
                f"  {name:45s} R@5={m.get('recall@5', 0):.4f} "
                f"CI95=[{ci['lo']:.4f}, {ci['hi']:.4f}]"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())