from __future__ import annotations

from typing import Dict, List


def _authority_names(authorities) -> List[str]:
    names = []
    for item in authorities:
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                names.append(str(name))
        elif isinstance(item, str):
            names.append(item)
    return names


def build_context(ranked_hits: List[Dict], top_k: int = 3) -> Dict:
    """Builds compact RAG context from retrieved legal cases."""
    if not ranked_hits:
        return {
            "primary": None,
            "alternatives": [],
            "context_items": [],
        }

    selected = ranked_hits[:top_k]
    context_items = []

    for item in selected:
        case = item.get("case", {})
        context_items.append(
            {
                "category": case.get("category", "Unknown"),
                "subcategory": case.get("subcategory", "Unknown"),
                "semantic_score": round(float(item.get("semantic_score", 0.0)), 4),
                "confidence_score": round(float(item.get("final_score", 0.0)), 4),
                "problem_description": case.get("problem_description", ""),
                "steps": case.get("workflow_steps", [])[:6],
                "documents": case.get("required_documents", [])[:8],
                "authorities": _authority_names(case.get("authorities", []))[:8],
                "online_portals": case.get("online_portals", [])[:6],
                "helplines": case.get("helplines", [])[:6],
            }
        )

    primary = context_items[0]
    alternatives = [
        {
            "category": entry["category"],
            "subcategory": entry["subcategory"],
            "confidence_score": entry["confidence_score"],
        }
        for entry in context_items[1:]
    ]

    return {
        "primary": primary,
        "alternatives": alternatives,
        "context_items": context_items,
    }
