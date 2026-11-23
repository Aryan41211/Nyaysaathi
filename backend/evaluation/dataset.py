"""Build auto-generated evaluation queries from the NyaySaathi corpus.

Queries are derived from case subcategories and problem descriptions.
Relevance judgments are AUTO-GENERATED: a case is relevant to a query if it
shares the same category as the query's source case. This is a proxy label,
NOT human-validated, and is clearly marked as such.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from evaluation import EvalQuery


def _first_clause(text: str) -> str:
    """Take the first sentence/clause of a description as a query phrase."""
    if not text:
        return ""
    clause = str(text).split(".")[0].strip()
    if len(clause) < 6:
        clause = str(text)[:80].strip()
    return clause


def build_auto_generated_dataset(
    cases: List[Dict[str, Any]],
    output_path: str | None = None,
) -> List[EvalQuery]:
    """Build an auto-generated evaluation dataset from the case corpus.

    For each case, the query is formed from the subcategory plus the first
    clause of the problem description. A case is relevant to a query if it
    shares the same ``category`` as the source case.

    Args:
        cases: List of normalized case dicts (must have ``id``, ``category``,
            ``subcategory``, ``problem_description``).
        output_path: Optional path to write the dataset JSON.

    Returns:
        List of EvalQuery objects with auto-generated labels.

    NOTE: These labels are auto-generated proxies, not human-validated.
    """
    queries: List[EvalQuery] = []

    # Group cases by category for relevance judgments. Values are index
    # positions in the cases list (used as canonical case IDs).
    category_to_indices: Dict[str, List[int]] = {}
    for idx, case in enumerate(cases):
        cat = str(case.get("category", "")).strip()
        if cat:
            category_to_indices.setdefault(cat, []).append(idx)

    for idx, case in enumerate(cases):
        subcategory = str(case.get("subcategory", ""))
        description = str(case.get("problem_description", ""))
        category = str(case.get("category", ""))

        query_text = f"{subcategory}: {_first_clause(description)}"
        if not query_text.strip():
            query_text = subcategory or "legal query"

        # Relevant cases: same category as source case (by index position).
        relevant_indices = list(category_to_indices.get(category, []))

        queries.append(
            EvalQuery(
                query_id=f"auto-{idx:04d}",
                query_text=query_text,
                relevant_case_ids=[str(i) for i in relevant_indices],
                label_source="auto-generated",
                metadata={
                    "source_case_index": idx,
                    "source_category": category,
                    "source_subcategory": subcategory,
                },
            )
        )

    if output_path:
        from backend.evaluation import save_dataset

        save_dataset(queries, Path(output_path))

    return queries


def build_human_validated_dataset_placeholder() -> List[EvalQuery]:
    """Placeholder for a human-validated evaluation dataset.

    No human-validated labels exist in the repository. This function returns
    an empty list and documents what would be needed to create one.

    To create a human-validated dataset:
    1. Select 50-100 diverse legal queries covering all 10 categories.
    2. For each query, have a legal expert identify relevant case IDs.
    3. Optionally assign relevance grades (0-3) for nDCG computation.
    4. Label each query with label_source="human-validated".
    5. Save to backend/evaluation/datasets/human_validated.json.
    """
    return []
