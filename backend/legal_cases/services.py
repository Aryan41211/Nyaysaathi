"""services.py - Search and retrieval logic for NyaySaathi.

This service layer now uses semantic intent matching (FAISS + sentence-transformers)
via search.semantic_engine while keeping the same public API used by views.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from services.search import reset_engine, semantic_search

from .db_connection import get_client

logger = logging.getLogger(__name__)

_cases_cache: List[Dict] = []
_mongo_unavailable = False

_LOCAL_DATA_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "nyaysaathi_part1.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_part2.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_part3.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_hindi.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_marathi.json",
]


def _load_cases_from_local_file() -> List[Dict]:
    merged: List[Dict] = []
    for candidate in _LOCAL_DATA_CANDIDATES:
        if not candidate.exists():
            logger.warning("Local fallback not found: %s", candidate)
            continue
        try:
            with candidate.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                merged.extend(raw)
                logger.warning("Loaded %d records from local fallback: %s", len(raw), candidate)
        except Exception as exc:
            logger.exception("Failed loading local fallback %s: %s", candidate, exc)
    if merged:
        logger.warning("Total local fallback records: %d", len(merged))
    return merged


def _load_cases() -> List[Dict]:
    global _cases_cache
    global _mongo_unavailable
    if not _cases_cache:
        if not _mongo_unavailable:
            try:
                # Outage-safe path: use a quick probe so search doesn't block on long Mongo retries.
                client = get_client(raise_on_error=False, quick=True)
                if client is None:
                    raise RuntimeError("Mongo unavailable (quick mode)")
                col = client[settings.MONGODB_DB]["legal_cases"]
                _cases_cache = list(col.find({}, {"_id": 0}))
                logger.info("Loaded %d cases from MongoDB", len(_cases_cache))
            except Exception as exc:
                _mongo_unavailable = True
                logger.warning("Mongo unavailable, switching to local dataset fallback: %s", exc)
        if not _cases_cache:
            _cases_cache = _load_cases_from_local_file()
    return _cases_cache


def invalidate_cache() -> None:
    """Invalidate in-memory case and search caches.

    Called after dataset import/update.
    """
    global _cases_cache
    global _mongo_unavailable
    _cases_cache = []
    _mongo_unavailable = False
    reset_engine()
    logger.info("Search cache invalidated")


def _keyword_fallback_search(cases: List[Dict], query: str, top_k: int) -> Tuple[List[Dict], Dict]:
    tokens = [t for t in query.lower().split() if len(t) > 1]
    if not tokens:
        return [], {
            "detected_language": "Unknown",
            "normalized_query": query,
            "search_ready_query": query,
            "keywords": [],
            "problem_domain": "Unknown",
            "problem_type": "General",
            "likely_authority": "District Legal Services Authority",
            "confidence": "Low",
            "nlp_source": "keyword_fallback",
        }

    ranked: List[Dict] = []
    for case in cases:
        haystack_parts = [
            str(case.get("category", "")),
            str(case.get("subcategory", "")),
            str(case.get("problem_description", "")),
            " ".join(case.get("keywords", []) or []),
        ]
        haystack = " ".join(haystack_parts).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score <= 0:
            continue

        out = dict(case)
        norm_score = min(1.0, score / max(1, len(tokens)))
        out["similarity_score"] = round(float(norm_score), 4)
        out["score"] = round(float(norm_score), 4)
        out["confidence"] = "High" if norm_score >= 0.8 else ("Medium" if norm_score >= 0.5 else "Low")
        out["match_type"] = "keyword_fallback"
        ranked.append(out)

    ranked.sort(key=lambda row: float(row.get("similarity_score", 0.0)), reverse=True)
    limited = ranked[:top_k]
    confidence = limited[0].get("confidence", "Low") if limited else "Low"
    return limited, {
        "detected_language": "Unknown",
        "normalized_query": query,
        "search_ready_query": query,
        "keywords": tokens,
        "problem_domain": "Unknown",
        "problem_type": "General",
        "likely_authority": "District Legal Services Authority",
        "confidence": confidence,
        "nlp_source": "keyword_fallback",
    }


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

    # Outage mode: if Mongo is unavailable, skip semantic model loading entirely
    # and return fast keyword fallback to keep search responsive.
    if _mongo_unavailable:
        return _keyword_fallback_search(cases, query, top_k)

    try:
        results, nlp_meta = semantic_search(cases=cases, query=query, top_k=top_k)
        if results:
            return results, nlp_meta
        logger.warning("Semantic search returned no results; using keyword fallback")
        return _keyword_fallback_search(cases, query, top_k)
    except Exception as exc:
        logger.exception("Semantic search failed for query %r: %s", query, exc)
        return _keyword_fallback_search(cases, query, top_k)


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
