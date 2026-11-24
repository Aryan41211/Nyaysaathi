from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from api.search_engine import simple_search

from .bm25_index import BM25Index
from .cross_encoder_reranker import CrossEncoderReranker
from .hybrid_retrieval import HybridRetriever
from .ranker import rank_results
from .semantic_engine import get_semantic_engine


logger = logging.getLogger(__name__)

# Hybrid retriever singleton (initialized lazily on first use).
_HYBRID_RETRIEVER: Optional[HybridRetriever] = None


def _get_hybrid_retriever() -> HybridRetriever:
    """Build and cache the hybrid retriever (dense-weighted fusion)."""
    global _HYBRID_RETRIEVER
    if _HYBRID_RETRIEVER is None:
        engine = get_semantic_engine()
        engine.ensure_ready()
        bm25_index = BM25Index(engine.get_cases())
        _HYBRID_RETRIEVER = HybridRetriever(
            semantic_engine=engine,
            bm25_index=bm25_index,
            use_tfidf=True,
            use_bm25=True,
            use_dense=True,
            top_k=5,
            fusion="weighted",
            weights={"tfidf": 0.1, "bm25": 0.2, "dense": 0.7},
        )
    return _HYBRID_RETRIEVER


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
    engine.ensure_ready()

    # Primary retrieval: weighted hybrid (TF-IDF + BM25 + dense).
    hybrid = _get_hybrid_retriever()
    hybrid_results = hybrid.search(processed["expanded_text"], top_k=max(5, top_k))
    logger.info(
        "hybrid_hits=%s for query='%s'", len(hybrid_results), safe_query
    )

    if hybrid_results:
        # Convert hybrid results to the rank_results-compatible format.
        semantic_hits = [
            {
                "case": item.get("case", item),
                "semantic_score": float(item.get("semantic_score", 0.0)),
                "_hybrid_score": float(item.get("fused_score", 0.0)),
                "_retrieval_source": item.get("retrieval_source", "hybrid"),
            }
            for item in hybrid_results
        ]
    else:
        # Fallback: semantic-only search.
        semantic_hits = engine.search(processed["expanded_text"], top_k=max(5, top_k))
        logger.info(
            "semantic_fallback_hits=%s for query='%s'", len(semantic_hits), safe_query
        )

        if not semantic_hits:
            semantic_hits = engine.keyword_search(
                processed["expanded"], top_k=max(5, top_k)
            )
            logger.info(
                "keyword_fallback_hits=%s for query='%s'", len(semantic_hits), safe_query
            )

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


# ============================================================================
# Multi-Query Expansion for Improved Retrieval Recall
# ============================================================================

ENHANCED_HINGLISH = {
    # Property/Land
    "kabja": "encroachment", "kabza": "encroachment", "zameen": "land",
    "jameen": "land", "plot": "land", "khasra": "land record",
    "khatauni": "land record", "jamabandi": "land record",
    "satbara": "7/12 extract", "7/12": "land record extract",
    "malmatta": "property card", "talathi": "revenue officer",
    "tehsildar": "revenue officer", "sarpanch": "village head",
    "panchayat": "village council",
    # Employment/Labour
    "salary nahi mila": "salary not paid", "job se nikal diya": "wrongful termination",
    "pf kate nahi": "PF not deducted", "esi nahi": "ESI not available",
    "overtime": "extra hours work", "naukri chhodi": "resignation",
    # Family
    "dahej": "dowry", "talaq": "divorce", "khula": "divorce",
    "bharan poshan": "maintenance", "custody": "child custody",
    "sasural": "in-laws house", "sasur": "father-in-law",
    "saas": "mother-in-law", "devar": "brother-in-law",
    # Cyber
    "upi fraud": "upi scam", "cyber thagi": "cyber fraud",
    "otp scam": "otp fraud", "phishing": "fraudulent email",
    "loan app": "digital lending app", "recovery agent": "debt collector",
    # Consumer
    "waranty": "warranty", "guarantee": "warranty", "refund": "money back",
    "vas": "value added service", "spam": "unsolicited message",
    # Police
    "fir": "first information report", "than": "police station",
    "chori": "theft", "dacoity": "robbery", "marpeet": "assault",
    # Government
    "ration card": "food subsidy card", "aadhaar": "national ID",
    "pension": "retirement benefit", "tehsil": "revenue office",
    "pas": "housing scheme", "bijli": "electricity",
    # Tenant
    "security deposit": "advance rent", "lease": "rental agreement",
    "eviction": "vacate notice", "rent agreement": "rental contract",
    # Environment
    "pradushan": "pollution", "kada": "waste", "nala": "drain",
    "avakh": "illegal mining",
    # Senior Citizen
    "vriddha": "elderly", "pension roka": "pension stopped",
    "ashram": "old age home",
}

ENHANCED_SYNONYMS = {
    "encroachment": ["illegal occupation", "trespass", "land grabbing"],
    "boundary": ["border", "demarcation", "survey line"],
    "landlord": ["owner", "lessor", "property owner"],
    "tenant": ["renter", "lessee"],
    "termination": ["firing", "dismissal", "layoff", "retrenchment"],
    "severance": ["compensation", "gratuity", "settlement"],
    "salary": ["wages", "pay", "remuneration", "emolument"],
    "dowry": ["dahej", "bridal gift demand"],
    "maintenance": ["alimony", "bharan poshan", "support"],
    "custody": ["guardianship", "child care"],
    "fraud": ["cheating", "scam", "deception"],
    "phishing": ["fraudulent email", "social engineering"],
    "defective": ["faulty", "damaged", "broken"],
    "warranty": ["guarantee", "warrantee"],
    "assault": ["beating", "physical attack", "violence"],
    "theft": ["stealing", "robbery", "burglary"],
    "certificate": ["document", "proof", "license"],
    "subsidy": ["grant", "financial aid", "benefit"],
}


def expand_query_variants(query: str, max_variants: int = 5) -> list[str]:
    """Generate multiple query variants for multi-query retrieval.

    Each variant is a different formulation of the same legal query:
    - Original text
    - Normalized text (Hinglish → English, stopwords removed)
    - Synonym-expanded text
    - Hinglish-mapped text (Indian legal terms → English)
    - Combined expansion

    Returns a list of unique query strings, ordered by relevance.
    """
    import re as _re

    variants = [query.strip()]

    normalized = normalize_text(query)
    if normalized and normalized != query.lower().strip():
        variants.append(normalized)

    tokens = tokenize(normalized)
    expanded = expand_synonyms(tokens)
    expanded = expand_phrase_synonyms(normalized, expanded)
    expanded_text = " ".join(expanded)
    if expanded_text and expanded_text != normalized:
        variants.append(expanded_text)

    enhanced_tokens = []
    for token in tokens:
        enhanced_tokens.append(token)
        for syn in ENHANCED_SYNONYMS.get(token, []):
            enhanced_tokens.append(syn)
    enhanced_text = " ".join(dict.fromkeys(enhanced_tokens))
    if enhanced_text and enhanced_text != normalized:
        variants.append(enhanced_text)

    hinglish_text = normalized.lower()
    for src, target in sorted(ENHANCED_HINGLISH.items(), key=lambda x: -len(x[0])):
        hinglish_text = _re.sub(rf"\b{_re.escape(src)}\b", target, hinglish_text)
    if hinglish_text and hinglish_text != normalized:
        variants.append(hinglish_text)

    # Deduplicate while preserving order, cap at max_variants.
    seen = set()
    unique = []
    for v in variants:
        v_clean = v.strip()
        if v_clean and v_clean not in seen:
            seen.add(v_clean)
            unique.append(v_clean)
            if len(unique) >= max_variants:
                break

    return unique
