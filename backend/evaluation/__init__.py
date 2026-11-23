"""NyaySaathi retrieval evaluation framework.

Provides:
- An evaluation dataset schema with clearly-labeled relevance judgments.
- Retrieval metrics: Recall@K, Precision@K, MRR, nDCG@K.
- A runner that compares TF-IDF, BM25, dense MiniLM+FAISS, and hybrid retrieval
  using identical queries and labels for a fair comparison.

Relevance labels can be:
- AUTO-GENERATED: derived from case category matching (proxy, LOW confidence).
- HUMAN-VALIDATED: manually labeled (HIGH confidence).

No human-validated labels exist in the repository; all labels are auto-generated.
This is clearly distinguished throughout.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

LabelSource = str  # "auto-generated" | "human-validated"


@dataclass
class EvalQuery:
    """A single evaluation query with relevance judgments."""

    query_id: str
    query_text: str
    relevant_case_ids: List[str]  # case IDs considered relevant
    relevance_grades: Dict[str, int] = field(default_factory=dict)  # case_id -> grade (0-3)
    label_source: LabelSource = "auto-generated"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result for a single query."""

    query_id: str
    query_text: str
    retrieved_case_ids: List[str]
    ranked_relevant: List[bool]  # relevance per retrieved position
    recall_at_k: Dict[int, float]
    precision_at_k: Dict[int, float]
    mrr: float
    ndcg_at_k: Dict[int, float]


@dataclass
class EvaluationReport:
    """Aggregate evaluation report for a retrieval system."""

    system_name: str
    n_queries: int
    label_source: LabelSource
    metrics: Dict[str, float]  # mean recall@k, precision@k, mrr, ndcg@k
    per_query: List[EvalResult] = field(default_factory=list)


def recall_at_k(ranked_relevant: List[bool], k: int, n_relevant: int) -> float:
    if n_relevant == 0:
        return 0.0
    return float(sum(ranked_relevant[:k]) / n_relevant)


def precision_at_k(ranked_relevant: List[bool], k: int) -> float:
    if k == 0:
        return 0.0
    return float(sum(ranked_relevant[:k]) / k)


def mrr(ranked_relevant: List[bool]) -> float:
    for i, rel in enumerate(ranked_relevant, start=1):
        if rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked_relevant: List[bool], k: int, n_relevant: int) -> float:
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


def evaluate_single_query(
    query: EvalQuery,
    retrieved_case_ids: List[str],
    k_values: List[int] = None,
) -> EvalResult:
    """Compute metrics for a single query given retrieved case IDs."""
    if k_values is None:
        k_values = [1, 3, 5, 10]

    ranked_relevant = [cid in query.relevant_case_ids for cid in retrieved_case_ids]
    n_relevant = len(query.relevant_case_ids)

    recall = {k: recall_at_k(ranked_relevant, k, n_relevant) for k in k_values}
    precision = {k: precision_at_k(ranked_relevant, k) for k in k_values}
    mrr_score = mrr(ranked_relevant)
    ndcg = {k: ndcg_at_k(ranked_relevant, k, n_relevant) for k in k_values}

    return EvalResult(
        query_id=query.query_id,
        query_text=query.query_text,
        retrieved_case_ids=retrieved_case_ids,
        ranked_relevant=ranked_relevant,
        recall_at_k=recall,
        precision_at_k=precision,
        mrr=mrr_score,
        ndcg_at_k=ndcg,
    )


def aggregate(results: List[EvalResult], system_name: str, label_source: LabelSource) -> EvaluationReport:
    """Aggregate per-query results into a system-level report."""
    if not results:
        return EvaluationReport(
            system_name=system_name,
            n_queries=0,
            label_source=label_source,
            metrics={},
        )

    k_values = sorted({k for r in results for k in r.recall_at_k.keys()})
    metrics: Dict[str, float] = {}
    for k in k_values:
        metrics[f"recall@{k}"] = statistics.mean(r.recall_at_k[k] for r in results)
        metrics[f"precision@{k}"] = statistics.mean(r.precision_at_k[k] for r in results)
        metrics[f"ndcg@{k}"] = statistics.mean(r.ndcg_at_k[k] for r in results)
    metrics["mrr"] = statistics.mean(r.mrr for r in results)

    return EvaluationReport(
        system_name=system_name,
        n_queries=len(results),
        label_source=label_source,
        metrics=metrics,
        per_query=results,
    )


def load_dataset(path: Path) -> List[EvalQuery]:
    """Load an evaluation dataset from a JSON file.

    Expected JSON format: a list of objects with keys:
    query_id, query_text, relevant_case_ids, relevance_grades (optional),
    label_source (optional), metadata (optional).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    queries: List[EvalQuery] = []
    for item in data:
        queries.append(
            EvalQuery(
                query_id=item["query_id"],
                query_text=item["query_text"],
                relevant_case_ids=list(item.get("relevant_case_ids", [])),
                relevance_grades=item.get("relevance_grades", {}),
                label_source=item.get("label_source", "auto-generated"),
                metadata=item.get("metadata", {}),
            )
        )
    return queries


def save_dataset(queries: List[EvalQuery], path: Path) -> None:
    """Save an evaluation dataset to a JSON file."""
    data = [
        {
            "query_id": q.query_id,
            "query_text": q.query_text,
            "relevant_case_ids": q.relevant_case_ids,
            "relevance_grades": q.relevance_grades,
            "label_source": q.label_source,
            "metadata": q.metadata,
        }
        for q in queries
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
