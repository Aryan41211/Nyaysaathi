from __future__ import annotations

from typing import Dict, List


CATEGORY_HINTS = {
    "cyber": ["upi", "online", "fraud", "cyber", "scam", "otp", "phishing"],
    "land": ["land", "property", "encroachment", "kabja", "boundary", "zameen"],
    "salary": ["salary", "wage", "employer", "job", "termination"],
}


def keyword_overlap_score(expanded_tokens: List[str], case_text: str) -> float:
    if not expanded_tokens:
        return 0.0

    text = case_text.lower()
    overlap = sum(1 for token in expanded_tokens if token in text)
    return min(1.0, overlap / max(1, len(expanded_tokens)))


def category_relevance_score(expanded_text: str, category: str, subcategory: str) -> float:
    blob = f"{category} {subcategory}".lower()
    query = expanded_text.lower()

    best = 0.0
    for hints in CATEGORY_HINTS.values():
        hits_query = sum(1 for hint in hints if hint in query)
        if hits_query == 0:
            continue
        hits_case = sum(1 for hint in hints if hint in blob)
        best = max(best, min(1.0, (hits_query * 0.6 + hits_case) / max(1.0, len(hints) / 2)))

    return best


def rank_hits(processed_query: Dict, hits: List[Dict], top_k: int = 5) -> List[Dict]:
    expanded = processed_query.get("expanded", [])
    expanded_text = processed_query.get("expanded_text", "")

    ranked = []
    for item in hits:
        case = item["case"]
        semantic_score = float(item.get("semantic_score", 0.0))
        keyword_score = keyword_overlap_score(expanded, case.get("searchable_text", ""))
        category_score = category_relevance_score(
            expanded_text,
            case.get("category", ""),
            case.get("subcategory", ""),
        )

        final_score = 0.72 * semantic_score + 0.18 * keyword_score + 0.10 * category_score
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
    return ranked[:top_k]
