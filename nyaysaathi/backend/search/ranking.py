"""Hybrid ranking utilities for NyaySaathi semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from rapidfuzz import fuzz


@dataclass
class RankedResult:
    case: Dict
    semantic_score: float
    keyword_overlap_score: float
    title_similarity_score: float
    final_score: float


def keyword_overlap(query_keywords: List[str], case_keywords: List[str]) -> float:
    """Compute normalized keyword overlap [0,1]."""
    q = {k.lower() for k in query_keywords if k}
    c = {k.lower() for k in case_keywords if k}
    if not q or not c:
        return 0.0
    return len(q.intersection(c)) / max(1, len(q))


def title_similarity(query_text: str, title_text: str) -> float:
    """Fuzzy title similarity [0,1]."""
    return fuzz.token_set_ratio(query_text, title_text) / 100.0


def hybrid_score(semantic: float, overlap: float, title: float) -> float:
    """Weighted score: semantic 70%, keyword overlap 20%, title similarity 10%."""
    return (0.7 * semantic) + (0.2 * overlap) + (0.1 * title)


def confidence_bucket(score: float) -> str:
    """Map final score to confidence label."""
    if score > 0.75:
        return "High"
    if score >= 0.50:
        return "Medium"
    return "Low"


def select_by_confidence(sorted_cases: List[Dict]) -> List[Dict]:
    """Apply response count behavior based on best confidence bucket."""
    if not sorted_cases:
        return []

    best_conf = sorted_cases[0].get("confidence", "Low")
    if best_conf == "High":
        return sorted_cases[:1]
    if best_conf == "Medium":
        return sorted_cases[:3]
    return sorted_cases[:5]
