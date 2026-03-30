from __future__ import annotations

import logging
import re
from typing import Dict, List

from api.search_engine import simple_search

from .ranker import rank_results
from .semantic_engine import get_semantic_engine


logger = logging.getLogger(__name__)


HINGLISH_NORMALIZATION = {
    "kabja": "encroachment",
    "kabza": "encroachment",
    "zameen": "land",
    "jameen": "land",
    "dhokha": "fraud",
    "cheated": "fraud",
    "fraud hua": "scammed",
    "thagi": "scam",
    "thana": "police station",
    "marpeet": "assault",
    "dahej": "dowry",
    "talaq": "divorce",
    "salary nahi mila": "salary not paid",
    "job se nikal diya": "wrongful termination",
    "salary nahi mila": "salary not paid",
    "salary nahi di": "salary not paid",
    "nahi mila": "not paid",
    "not received": "not paid",
    "cyber thagi": "cyber fraud",
    "upi fraud": "upi scam",
}

SYNONYM_MAP = {
    "occupy": ["encroachment", "illegal occupation"],
    "occupied": ["encroachment", "illegal occupation"],
    "scammed": ["fraud", "cyber fraud"],
    "scam": ["fraud", "cyber fraud"],
    "fraud": ["cheating", "cyber fraud"],
    "not": ["unpaid"],
    "paid": ["salary issue"],
    "employer": ["company", "boss"],
    "company": ["employer", "boss"],
    "unpaid": ["salary issue", "salary dispute"],
    "land": ["property", "land dispute"],
    "threat": ["intimidation", "criminal threat"],
    "beaten": ["assault", "physical violence"],
    "salary": ["wage", "labour", "salary dispute", "salary non-payment"],
    "fired": ["termination", "wrongful termination"],
    "upi": ["digital payment", "cyber fraud"],
}

PHRASE_SYNONYMS = {
    "not paid": ["unpaid", "salary issue"],
    "salary not paid": ["unpaid", "salary dispute", "labour issue"],
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "to",
    "for",
    "of",
    "in",
    "on",
    "through",
    "my",
    "me",
    "meri",
    "mera",
    "mujhe",
    "par",
    "ko",
    "ne",
    "ki",
    "ka",
    "ke",
    "ho",
    "gaya",
    "hai",
    "someone",
}


def _unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in items:
        term = item.strip()
        if not term or term in seen:
            continue
        seen.add(term)
        ordered.append(term)
    return ordered


def normalize_text(text: str) -> str:
    """Normalize user text to a clean lowercase English-like form."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)

    # Replace longer phrases first to avoid partial substitutions.
    for src in sorted(HINGLISH_NORMALIZATION.keys(), key=len, reverse=True):
        target = HINGLISH_NORMALIZATION[src]
        text = re.sub(rf"\b{re.escape(src)}\b", target, text)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    """Split normalized text and remove stopwords."""
    return [token for token in text.split() if token and token not in STOPWORDS]


def expand_synonyms(tokens: List[str]) -> List[str]:
    """Expand each token with domain synonyms while preserving order."""
    expanded: List[str] = []
    for token in tokens:
        expanded.append(token)
        for synonym in SYNONYM_MAP.get(token, []):
            expanded.append(synonym)
    return _unique_preserve_order(expanded)


def expand_phrase_synonyms(normalized_text: str, expanded_tokens: List[str]) -> List[str]:
    output = list(expanded_tokens)
    for phrase, mapped in PHRASE_SYNONYMS.items():
        if phrase in normalized_text:
            output.extend(mapped)
    return _unique_preserve_order(output)


def process_query_text(query: str) -> Dict:
    """Build normalized query artifacts used by downstream retrieval."""
    normalized = normalize_text(query)
    tokens = tokenize(normalized)
    expanded = expand_synonyms(tokens)
    expanded = expand_phrase_synonyms(normalized, expanded)

    return {
        "normalized": normalized,
        "tokens": tokens,
        "expanded": expanded,
        "expanded_text": " ".join(expanded),
    }


def _confidence_band(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def process_query(query: str, top_k: int = 5) -> dict:
    """Full NLP retrieval pipeline entrypoint for API search."""
    safe_query = "" if query is None else str(query)
    processed = process_query_text(safe_query)

    if not processed["normalized"]:
        return {
            "status": "fail",
            "message": "Empty query",
            "data": [],
            "nlp": {
                "understood_as": "",
                "detected_language": "en",
                "confidence": "Low",
                "keywords": [],
                "nlp_source": "semantic+fallback",
            },
            "clarification_required": True,
            "clarification_message": "Please describe your legal problem in one sentence.",
            "clarification_questions": [
                "What happened?",
                "Who is involved?",
                "When did it happen?",
            ],
            "query_analysis": processed,
        }

    engine = get_semantic_engine()

    semantic_hits = engine.search(processed["expanded_text"], top_k=max(5, top_k))
    logger.info("semantic_hits=%s for query='%s'", len(semantic_hits), safe_query)

    if not semantic_hits:
        semantic_hits = engine.keyword_search(processed["expanded"], top_k=max(5, top_k))
        logger.info("keyword_fallback_hits=%s for query='%s'", len(semantic_hits), safe_query)

    ranked = rank_results(processed, semantic_hits, top_k=max(5, top_k))

    # Final safety net: legacy keyword search over descriptions.
    if not ranked:
        fallback_cases = simple_search(safe_query)
        ranked = [
            {
                "case": case,
                "semantic_score": 0.35,
                "keyword_score": 0.35,
                "category_score": 0.35,
                "final_score": 0.35,
            }
            for case in fallback_cases[: max(3, top_k)]
        ]
        logger.info("legacy_fallback_hits=%s for query='%s'", len(ranked), safe_query)

    cases = []
    for item in ranked:
        case = dict(item["case"])
        case["score"] = round(float(item.get("final_score", 0.0)), 4)
        cases.append(case)

    confidence_score = max([case.get("score", 0.0) for case in cases], default=0.0)

    return {
        "status": "success",
        "data": cases,
        "nlp": {
            "understood_as": processed["expanded_text"],
            "detected_language": "en",
            "confidence": _confidence_band(confidence_score),
            "keywords": processed["expanded"][:8],
            "nlp_source": "semantic+fallback",
        },
        "clarification_required": False,
        "clarification_message": "",
        "clarification_questions": [],
        "query_analysis": processed,
    }
