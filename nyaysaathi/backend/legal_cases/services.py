"""services.py - Search and retrieval logic for NyaySaathi.

This service layer now uses semantic intent matching (FAISS + sentence-transformers)
via search.semantic_engine while keeping the same public API used by views.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from services.search import reset_engine, semantic_search

from .db_connection import get_collection

logger = logging.getLogger(__name__)

_cases_cache: List[Dict] = []


def _load_cases() -> List[Dict]:
    global _cases_cache
    if not _cases_cache:
        col = get_collection("legal_cases")
        _cases_cache = list(col.find({}, {"_id": 0}))
        logger.info("Loaded %d cases from MongoDB", len(_cases_cache))
    return _cases_cache


def invalidate_cache() -> None:
    """Invalidate in-memory case and search caches.

    Called after dataset import/update.
    """
    global _cases_cache
    _cases_cache = []
    reset_engine()
    logger.info("Search cache invalidated")


def search_cases(query: str, top_k: int = 5) -> Tuple[List[Dict], Dict]:
    """Main semantic search entrypoint.

    Returns:
        tuple(results, nlp_meta)
    """
    if not query or not query.strip():
        return [], {}

    cases = _load_cases()
    if not cases:
        logger.error("No legal cases found in MongoDB")
        return [], {}

    try:
        results, nlp_meta = semantic_search(cases=cases, query=query, top_k=top_k)
        return results, nlp_meta
    except Exception as exc:
        logger.exception("Semantic search failed for query %r: %s", query, exc)
        return [], {
            "detected_language": "Unknown",
            "normalized_query": query,
            "search_ready_query": query,
            "keywords": [],
            "problem_domain": "Unknown",
            "problem_type": "General",
            "likely_authority": "District Legal Services Authority",
            "confidence": "Low",
            "nlp_source": "semantic_error",
        }


def get_all_categories() -> List[Dict]:
    cases = _load_cases()
    cat_map = defaultdict(list)
    for c in cases:
        cat_map[c["category"]].append(c["subcategory"])
    return [
        {"category": cat, "subcategory_count": len(subs), "subcategories": subs}
        for cat, subs in sorted(cat_map.items())
    ]


def get_all_cases(category: Optional[str] = None) -> List[Dict]:
    cases = _load_cases()
    if category:
        cases = [c for c in cases if c.get("category", "").lower() == category.lower()]
    return cases


def get_case_by_subcategory(subcategory: str) -> Optional[Dict]:
    cases = _load_cases()
    sub_lower = subcategory.lower().strip()
    for c in cases:
        if c.get("subcategory", "").lower().strip() == sub_lower:
            return dict(c)
    return None
