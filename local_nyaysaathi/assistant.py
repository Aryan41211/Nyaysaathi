from __future__ import annotations

from typing import Dict

from .context_builder import build_context
from .query_understanding import process_query
from .ranker import rank_hits
from .response_generator import generate_response
from .semantic_search import get_retriever


def run_legal_assistant(query: str, top_k: int = 5) -> Dict:
    processed = process_query(query)

    if not processed["normalized"]:
        return {
            "query": query,
            "intent": processed.get("intent", "general_legal"),
            "matched_category": None,
            "matched_subcategory": None,
            "confidence_score": 0.0,
            "explanation": "Please enter a non-empty legal problem.",
            "steps": [],
            "documents": [],
            "authorities": [],
            "suggestions": [
                "Describe what happened and who is involved.",
                "Add useful facts like payment mode, timeline, and place.",
            ],
            "alternatives": [],
            "query_analysis": processed,
        }

    retriever = get_retriever()
    raw_hits = retriever.search(processed["expanded_text"], top_k=top_k)
    hits = [{"case": item.case, "semantic_score": item.semantic_score} for item in raw_hits]
    ranked = rank_hits(processed, hits, top_k=top_k)

    context = build_context(ranked, top_k=min(5, top_k))
    best_confidence = ranked[0]["final_score"] if ranked else 0.0

    response = generate_response(
        query=query,
        processed_query=processed,
        context=context,
        confidence_score=best_confidence,
    )

    response["query_analysis"] = processed
    response["matches"] = [
        {
            "category": item["case"].get("category", "Unknown"),
            "subcategory": item["case"].get("subcategory", "Unknown"),
            "confidence_score": round(item["final_score"], 4),
            "semantic_score": round(item["semantic_score"], 4),
            "keyword_score": round(item["keyword_score"], 4),
            "category_score": round(item["category_score"], 4),
        }
        for item in ranked
    ]

    primary = context.get("primary") or {}
    response["online_portals"] = primary.get("online_portals", [])
    response["helplines"] = primary.get("helplines", [])

    if retriever.model_error:
        response["engine_warning"] = (
            "Semantic model unavailable, keyword fallback retrieval was used. "
            f"Details: {retriever.model_error}"
        )

    return response
