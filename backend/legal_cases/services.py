"""services.py - Search and retrieval logic for NyaySaathi.

This service layer now uses semantic intent matching (FAISS + sentence-transformers)
via search.semantic_engine while keeping the same public API used by views.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from rapidfuzz import fuzz
from services.search import reset_engine, semantic_search
from search.query_processor import process_query as preprocess_query

from .observability import get_observability
from .response_validator import validate_response
from .db_connection import get_client

logger = logging.getLogger(__name__)

_cases_cache: List[Dict] = []
_mongo_unavailable = False
_SEMANTIC_MAX_CONCURRENCY = max(2, int(os.getenv("SEMANTIC_MAX_CONCURRENCY", "8")))
_SEARCH_CACHE_TTL_SECONDS = max(30, int(os.getenv("SEARCH_RESULT_CACHE_TTL_SECONDS", "180")))
_HOT_SEARCH_CACHE_TTL_SECONDS = max(
    _SEARCH_CACHE_TTL_SECONDS,
    int(os.getenv("HOT_SEARCH_RESULT_CACHE_TTL_SECONDS", "600")),
)
_HOT_QUERY_THRESHOLD = max(3, int(os.getenv("HOT_QUERY_THRESHOLD", "6")))
_OVERLOAD_ALLOW_KEYWORD_FALLBACK = str(os.getenv("OVERLOAD_ALLOW_KEYWORD_FALLBACK", "true")).strip().lower() in {
    "1",
    "true",
    "yes",
}
_SEMANTIC_SEMAPHORE = threading.BoundedSemaphore(_SEMANTIC_MAX_CONCURRENCY)

_LOCAL_DATA_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "nyaysaathi_part1.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_part2.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_part3.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_hindi.json",
    Path(__file__).resolve().parents[2] / "nyaysaathi_marathi.json",
]


def build_standard_response(query: str, results: List[Dict], nlp_meta: Dict) -> Dict:
    """Build normalized production response payload for API and debugging."""
    top = results[0] if results else {}
    safety = validate_response(query=query, results=results, nlp_meta=nlp_meta).to_dict()
    confidence = str(safety.get("confidence") or str((nlp_meta or {}).get("confidence") or "Low"))
    clarification_payload = dict(safety.get("clarification") or {})
    clarification_required = bool(clarification_payload.get("required", False))
    clarification_message = str(clarification_payload.get("message") or "")
    answer = str(safety.get("answer") or "")

    return {
        "intent": str((nlp_meta or {}).get("matched_intent") or "General legal issue"),
        "confidence": confidence,
        "answer": answer,
        "decision": str(safety.get("decision") or "clarification_only"),
        "disclaimer": str(safety.get("disclaimer") or ""),
        "intent_match": bool(safety.get("intent_match", False)),
        "clarification": {
            "required": clarification_required,
            "message": clarification_message,
            "questions": list(clarification_payload.get("questions") or []),
        },
        "structured": dict(safety.get("structured") or {}),
        "debug": {
            "query": query,
            "understood_as": str((nlp_meta or {}).get("understood_as") or (nlp_meta or {}).get("search_ready_query") or query),
            "language": str((nlp_meta or {}).get("detected_language") or "Unknown"),
            "keywords": list((nlp_meta or {}).get("keywords") or []),
            "scores": {
                "overall_confidence_score": float((nlp_meta or {}).get("overall_confidence_score") or 0.0),
                "intent_confidence_score": float((nlp_meta or {}).get("intent_confidence_score") or 0.0),
                "top_similarity_score": float(top.get("similarity_score") or 0.0),
            },
            "signals": dict((nlp_meta or {}).get("reasoning_signals") or {}),
            "safety": dict(safety.get("debug") or {}),
        },
    }


def _empty_nlp_meta(query: str, source: str = "keyword_fallback") -> Dict:
    return {
        "detected_language": "Unknown",
        "normalized_query": query,
        "search_ready_query": query,
        "understood_as": query,
        "keywords": [],
        "problem_domain": "Unknown",
        "problem_type": "General",
        "likely_authority": "District Legal Services Authority",
        "matched_intent": "General legal issue",
        "confidence": "Low",
        "overall_confidence_score": 0.0,
        "ambiguity_score": 1.0,
        "clarification_required": True,
        "clarification_message": "Please share more details so we can safely map your legal issue.",
        "clarification_questions": [
            "Who is the opposite party (employer, landlord, police, bank, etc.)?",
            "What happened and when did it start?",
            "What proof or documents do you currently have?",
        ],
        "reasoning_signals": {
            "top_similarity": 0.0,
            "top_margin": 0.0,
            "query_clarity": 0.0,
        },
        "nlp_source": source,
    }


def _normalize_nlp_meta(query: str, payload: Dict | None, source: str) -> Dict:
    meta = _empty_nlp_meta(query, source=source)
    if payload:
        meta.update(payload)

    confidence = str(meta.get("confidence", "Low")).strip().lower()
    meta["confidence"] = confidence.capitalize() if confidence else "Low"
    meta["understood_as"] = str(meta.get("understood_as") or meta.get("search_ready_query") or query)
    meta["clarification_required"] = bool(meta.get("clarification_required", meta["confidence"] == "Low"))
    meta["clarification_questions"] = list(meta.get("clarification_questions") or [])
    meta["reasoning_signals"] = dict(meta.get("reasoning_signals") or {})
    return meta


def _canonical_query_key(query: str) -> str:
    processed = preprocess_query(query)
    canonical = str(processed.expanded or processed.normalized or query).strip().lower()
    return " ".join(canonical.split())


def _result_cache_key(query: str, top_k: int) -> str:
    return f"search:result:v2:{_canonical_query_key(query)}:{int(top_k)}"


def _query_frequency_key(query: str) -> str:
    return f"search:freq:v1:{_canonical_query_key(query)}"


def _increment_query_frequency(query: str) -> int:
    key = _query_frequency_key(query)
    try:
        existing = int(cache.get(key, 0) or 0)
        new_value = existing + 1
        cache.set(key, new_value, timeout=3600)
        return new_value
    except Exception:
        return 1


def _read_cached_search(query: str, top_k: int) -> Tuple[List[Dict], Dict] | None:
    key = _result_cache_key(query, top_k)
    try:
        payload = cache.get(key)
        if not payload:
            return None
        results = list(payload.get("results") or [])
        nlp_meta = dict(payload.get("nlp_meta") or {})
        nlp_meta["cache_hit"] = True
        return results, nlp_meta
    except Exception:
        return None


def _write_cached_search(query: str, top_k: int, results: List[Dict], nlp_meta: Dict, frequency: int) -> None:
    ttl = _HOT_SEARCH_CACHE_TTL_SECONDS if frequency >= _HOT_QUERY_THRESHOLD else _SEARCH_CACHE_TTL_SECONDS
    key = _result_cache_key(query, top_k)
    try:
        cache.set(
            key,
            {
                "results": results,
                "nlp_meta": nlp_meta,
            },
            timeout=ttl,
        )
    except Exception:
        return


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
    processed = preprocess_query(query)
    tokens = [str(t).lower() for t in (processed.keywords or processed.tokens) if len(str(t)) > 1]
    if not tokens:
        return [], _normalize_nlp_meta(query, None, source="keyword_fallback")

    def infer_intent() -> tuple[str, str, str, str]:
        text = " ".join(tokens)
        if any(k in text for k in ["consumer", "refund", "warranty", "defect", "forum"]):
            return (
                "Consumer Complaint",
                "Consumer Complaints",
                "Defective Product/Service Dispute",
                "Consumer Forum",
            )
        if any(k in text for k in ["police", "fir", "thana", "station"]):
            return (
                "Police FIR Refusal",
                "Police Complaints and Local Crime",
                "Police Inaction",
                "Police",
            )
        if any(k in text for k in ["salary", "wage", "employer"]):
            return (
                "Salary Non-Payment",
                "Labour and Wage Issues",
                "Salary/Wage Dispute",
                "Labour Department",
            )
        if any(k in text for k in ["jhagda", "violence", "harassment", "family"]):
            return (
                "Domestic Violence / Family Safety",
                "Domestic Violence and Family Disputes",
                "Domestic Violence Protection",
                "Protection Officer / Court",
            )
        if any(k in text for k in ["landlord", "tenant", "deposit", "rent"]):
            return (
                "Tenant-Landlord Deposit Dispute",
                "Tenant-Landlord Disputes",
                "Security Deposit Dispute",
                "Rent Authority / Civil Court",
            )
        if any(k in text for k in ["fraud", "upi", "cyber", "scam"]):
            return (
                "UPI / Cyber Fraud",
                "Cyber Fraud and Digital Scams",
                "Digital Fraud",
                "Cyber Cell / Bank",
            )
        return (
            "General legal issue",
            "Unknown",
            "General",
            "District Legal Services Authority",
        )

    matched_intent, legal_domain, problem_type, authority = infer_intent()
    expanded_query = processed.expanded or query

    ranked: List[Dict] = []
    for case in cases:
        haystack_parts = [
            str(case.get("category", "")),
            str(case.get("subcategory", "")),
            str(case.get("problem_description", "")),
            " ".join(case.get("keywords", []) or []),
        ]
        haystack = " ".join(haystack_parts).lower()

        exact_hits = sum(1 for token in tokens if token in haystack)
        exact_ratio = exact_hits / max(1, len(tokens))
        fuzzy_ratio = fuzz.token_set_ratio(expanded_query.lower(), haystack) / 100.0
        score = (0.60 * exact_ratio) + (0.40 * fuzzy_ratio)

        if score < 0.26:
            continue

        out = dict(case)
        norm_score = min(1.0, score)
        out["similarity_score"] = round(float(norm_score), 4)
        out["score"] = round(float(norm_score), 4)
        out["confidence"] = "High" if norm_score >= 0.62 else ("Medium" if norm_score >= 0.45 else "Low")
        out["match_type"] = "keyword_fallback"
        out["matched_intent"] = matched_intent
        ranked.append(out)

    ranked.sort(key=lambda row: float(row.get("similarity_score", 0.0)), reverse=True)
    limited = ranked[:top_k]

    if not limited:
        # Last-resort fuzzy fallback over category/subcategory only.
        for case in cases:
            title = " ".join([str(case.get("category", "")), str(case.get("subcategory", ""))]).lower()
            fuzzy_ratio = fuzz.token_set_ratio(expanded_query.lower(), title) / 100.0
            if fuzzy_ratio < 0.42:
                continue
            out = dict(case)
            out["similarity_score"] = round(float(fuzzy_ratio), 4)
            out["score"] = round(float(fuzzy_ratio), 4)
            out["confidence"] = "High" if fuzzy_ratio >= 0.62 else ("Medium" if fuzzy_ratio >= 0.45 else "Low")
            out["match_type"] = "title_fuzzy_fallback"
            out["matched_intent"] = matched_intent
            limited.append(out)
            if len(limited) >= top_k:
                break

    confidence = limited[0].get("confidence", processed.confidence_hint) if limited else processed.confidence_hint
    if matched_intent != "General legal issue" and limited and float(processed.ambiguity_score) <= 0.35:
        confidence = "High"

    return limited, _normalize_nlp_meta(query, {
        "detected_language": processed.language,
        "normalized_query": processed.normalized or query,
        "search_ready_query": expanded_query,
        "understood_as": expanded_query,
        "keywords": tokens,
        "problem_domain": legal_domain,
        "problem_type": problem_type,
        "likely_authority": authority,
        "matched_intent": matched_intent,
        "confidence": confidence,
        "overall_confidence_score": float(limited[0].get("similarity_score", 0.0)) if limited else 0.0,
        "ambiguity_score": processed.ambiguity_score,
        "clarification_required": str(confidence).lower() == "low",
        "reasoning_signals": {
            "fallback_mode": 1.0,
            "token_count": float(len(tokens)),
            "query_clarity": round(1.0 - float(processed.ambiguity_score), 4),
        },
        "nlp_source": "keyword_fallback",
    }, source="keyword_fallback")


def search_cases(query: str, top_k: int = 5) -> Tuple[List[Dict], Dict]:
    """Main semantic search entrypoint.

    Returns:
        tuple(results, nlp_meta)
    """
    if not query or not query.strip():
        return [], _normalize_nlp_meta(query, None, source="empty_query")

    top_k = min(max(int(top_k), 1), 10)
    telemetry = get_observability()
    frequency = _increment_query_frequency(query)

    cached = _read_cached_search(query, top_k)
    if cached is not None:
        cached_results, cached_nlp = cached
        telemetry.record_decision(
            query=query,
            normalized_query=str(cached_nlp.get("search_ready_query") or cached_nlp.get("normalized_query") or query),
            intent=str(cached_nlp.get("matched_intent") or "General legal issue"),
            confidence=str(cached_nlp.get("confidence") or "Low"),
            decision="answer" if not bool(cached_nlp.get("clarification_required", False)) else "fallback",
            cache_hit=True,
            fallback=bool(cached_nlp.get("clarification_required", False)),
            latency_ms=0.0,
        )
        return cached_results, cached_nlp

    cases = _load_cases()
    if not cases:
        logger.error("No legal cases found from MongoDB/local fallback")
        return [], _normalize_nlp_meta(query, None, source="empty_dataset")

    semantic_on_outage = str(os.getenv("SEMANTIC_ON_MONGO_OUTAGE", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if _mongo_unavailable and not semantic_on_outage:
        logger.info("Mongo unavailable: using fast keyword fallback (SEMANTIC_ON_MONGO_OUTAGE=false)")
        fallback_results, fallback_meta = _keyword_fallback_search(cases, query, top_k)
        _write_cached_search(query, top_k, fallback_results, fallback_meta, frequency)
        return fallback_results, fallback_meta

    acquired = _SEMANTIC_SEMAPHORE.acquire(blocking=False)
    if not acquired and _OVERLOAD_ALLOW_KEYWORD_FALLBACK:
        logger.warning("Semantic engine overloaded; serving keyword fallback")
        fallback_results, fallback_meta = _keyword_fallback_search(cases, query, top_k)
        fallback_meta["nlp_source"] = "keyword_fallback_overload"
        fallback_meta["overload_shed"] = True
        _write_cached_search(query, top_k, fallback_results, fallback_meta, frequency)
        telemetry.record_decision(
            query=query,
            normalized_query=str(fallback_meta.get("search_ready_query") or fallback_meta.get("normalized_query") or query),
            intent=str(fallback_meta.get("matched_intent") or "General legal issue"),
            confidence=str(fallback_meta.get("confidence") or "Low"),
            decision="fallback",
            cache_hit=False,
            fallback=True,
            latency_ms=0.0,
        )
        return fallback_results, fallback_meta

    try:
        results, nlp_meta = semantic_search(cases=cases, query=query, top_k=top_k)
        nlp_meta = _normalize_nlp_meta(query, nlp_meta, source="semantic_engine")
        if results:
            _write_cached_search(query, top_k, results, nlp_meta, frequency)
            return results, nlp_meta

        logger.warning("Semantic search returned no results; using keyword fallback")
        fallback_results, fallback_meta = _keyword_fallback_search(cases, query, top_k)
        _write_cached_search(query, top_k, fallback_results, fallback_meta, frequency)
        return fallback_results, fallback_meta
    except Exception as exc:
        logger.exception("Semantic search failed for query %r: %s", query, exc)
        fallback_results, fallback_meta = _keyword_fallback_search(cases, query, top_k)
        fallback_meta["semantic_error"] = str(exc)
        _write_cached_search(query, top_k, fallback_results, fallback_meta, frequency)
        telemetry.record_error("semantic_search_error")
        return fallback_results, fallback_meta
    finally:
        if acquired:
            _SEMANTIC_SEMAPHORE.release()


def classify_case(query: str) -> Dict:
    """Unified classify pathway backed by the same guidance/search pipeline."""
    text = str(query or "").strip()

    def _classify_from_search_fallback() -> Dict:
        results, nlp_meta = search_cases(text, top_k=1)
        top = results[0] if results else {}
        return {
            "intent": str(nlp_meta.get("matched_intent") or "guidance"),
            "category": str(top.get("category") or "Unknown"),
            "confidence": str(nlp_meta.get("confidence") or "Low"),
            "similarity_score": float(top.get("similarity_score") or 0.0),
            "matched_text": str(top.get("subcategory") or ""),
            "workflow_steps": list(top.get("workflow_steps") or top.get("workflow") or []),
            "explanation": "Classification served by resilient local fallback.",
            "clarification_questions": list(nlp_meta.get("clarification_questions") or []),
            "problem_summary": str(nlp_meta.get("search_ready_query") or text),
            "source": "keyword_fallback",
            "clarification_required": bool(nlp_meta.get("clarification_required", False)),
            "request_id": "",
        }

    if not text:
        return {
            "intent": "guidance",
            "category": "Unknown",
            "confidence": "Low",
            "similarity_score": 0.0,
            "matched_text": "",
            "workflow_steps": ["Please describe problem more clearly"],
            "explanation": "Please provide your legal issue in one sentence.",
            "clarification_questions": [
                "Who is involved in your issue?",
                "What happened and when?",
            ],
            "problem_summary": "",
            "source": "services.classify_case",
            "clarification_required": True,
            "request_id": "",
        }

    # Avoid expensive workflow DB lookup when Mongo is down.
    try:
        if get_client(raise_on_error=False, quick=True) is None:
            return _classify_from_search_fallback()
    except Exception:
        return _classify_from_search_fallback()

    try:
        from ai_engine.response_generator import generate_legal_guidance

        guidance = generate_legal_guidance(text)
        nlp = dict(guidance.get("nlp") or {})

        workflow_steps = list(guidance.get("workflow_steps") or guidance.get("workflow") or [])
        if not workflow_steps:
            workflow_steps = ["Please answer clarification questions for a precise legal workflow."]

        return {
            "intent": str(nlp.get("matched_intent") or "guidance"),
            "category": str(guidance.get("category") or "Unknown"),
            "confidence": str(nlp.get("confidence") or "Low"),
            "similarity_score": float(nlp.get("overall_confidence_score") or 0.0),
            "matched_text": str(guidance.get("subcategory") or guidance.get("category") or ""),
            "workflow_steps": workflow_steps,
            "explanation": str(guidance.get("message") or "Guidance generated."),
            "clarification_questions": list(guidance.get("clarification_questions") or []),
            "problem_summary": str(guidance.get("normalized_query") or text),
            "source": str(nlp.get("nlp_source") or "semantic_engine"),
            "clarification_required": bool(guidance.get("clarification_required", False)),
            "request_id": str(guidance.get("request_id") or ""),
        }
    except Exception as exc:
        logger.exception("classify_case failed for query %r: %s", text, exc)
        return _classify_from_search_fallback()


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
