from __future__ import annotations

from typing import Dict, List, Set


CATEGORY_HINTS = {
    "cyber": ["upi", "otp", "phishing", "hack", "online fraud", "cyber"],
    "land": ["land", "zameen", "kabja", "encroachment", "property", "boundary"],
    "family": ["divorce", "maintenance", "custody", "domestic violence", "shaadi"],
    "labour": ["salary", "wage", "employer", "job", "termination"],
    "police": ["fir", "threat", "assault", "harassment", "abuse"],
}


def _token_set(text: str) -> Set[str]:
    return {token for token in text.lower().split() if token}


def keyword_overlap_score(query_terms: List[str], case_text: str) -> float:
    if not query_terms:
        return 0.0

    qset = set(query_terms)
    cset = _token_set(case_text)
    overlap = len(qset.intersection(cset))
    return min(1.0, overlap / max(1, len(qset)))


def category_relevance_score(query_text: str, category: str, subcategory: str) -> float:
    query_text = query_text.lower()
    category_text = f"{category} {subcategory}".lower()

    best = 0.0
    for _, hints in CATEGORY_HINTS.items():
        matched = sum(1 for h in hints if h in query_text)
        if matched == 0:
            continue
        category_hits = sum(1 for h in hints if h in category_text)
        score = min(1.0, (0.5 * matched + category_hits) / max(1, len(hints) / 2))
        best = max(best, score)

    if best == 0.0 and (category_text in query_text or subcategory.lower() in query_text):
        return 0.8

    return best


def rank_results(processed_query: Dict, semantic_hits: List[Dict], top_k: int = 5) -> List[Dict]:
    query_text = processed_query.get("expanded_text", processed_query.get("normalized", ""))
    query_terms = processed_query.get("expanded", processed_query.get("tokens", []))

    ranked = []
    for hit in semantic_hits:
        case = hit["case"]
        semantic_score = float(hit.get("semantic_score", 0.0))
        keyword_score = keyword_overlap_score(query_terms, case.get("searchable_text", ""))
        category_score = category_relevance_score(
            query_text,
            case.get("category", ""),
            case.get("subcategory", ""),
        )

        final_score = (0.65 * semantic_score) + (0.25 * keyword_score) + (0.10 * category_score)

        ranked.append(
            {
                "case": case,
                "semantic_score": semantic_score,
                "keyword_score": keyword_score,
                "category_score": category_score,
                "final_score": float(max(0.0, min(1.0, final_score))),
            }
        )

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    k = min(len(ranked), max(3, top_k))
    return ranked[:k]
