from __future__ import annotations

import json
import os
from typing import Dict, List, Optional


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _local_explanation(query: str, intent: str, context: Dict, confidence: float) -> str:
    primary = context.get("primary")
    if not primary:
        return (
            "I could not find a strong legal match. Please add more detail like where it happened, "
            "who was involved, and any documents or payment details."
        )

    subcategory = primary.get("subcategory", "this legal issue")
    category = primary.get("category", "legal category")
    confidence_band = _confidence_label(confidence)

    return (
        f"Based on your query, this looks like {subcategory} under {category}. "
        f"Intent detected: {intent}. Match confidence is {confidence_band}. "
        "The recommendation comes from semantic similarity, query intent clues, and overlap with legal workflow context."
    )


def _local_suggestions(intent: str, confidence: float, has_alternatives: bool) -> List[str]:
    suggestions = []

    if intent == "cyber_fraud":
        suggestions.append("Immediately secure your bank account, UPI PIN, and linked phone number.")
        suggestions.append("File a complaint on the National Cyber Crime Portal and preserve transaction evidence.")
    elif intent == "land_dispute":
        suggestions.append("Collect land records, ownership proof, and dated photos of the disputed property.")
        suggestions.append("Approach local revenue authorities before filing a civil suit.")
    elif intent == "labour_issue":
        suggestions.append("Keep salary slips, attendance proof, and employer communication records.")
        suggestions.append("File a written complaint with the Labour Office if unresolved.")
    elif intent == "family_issue":
        suggestions.append("Preserve messages, medical records, and any prior complaints.")
        suggestions.append("Seek legal aid support for maintenance, safety, or custody actions.")
    else:
        suggestions.append("Add timeline, location, and names of involved parties for better legal matching.")
        suggestions.append("Include evidence details like payments, notices, IDs, or witness info.")

    if confidence < 0.45:
        suggestions.append("Confidence is low; rephrase your query with specific facts and legal keywords.")

    if has_alternatives:
        suggestions.append("Review alternative matches as your issue may overlap multiple legal categories.")

    return suggestions[:4]


def _try_openai_response(query: str, intent: str, context: Dict) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)
        prompt = {
            "user_query": query,
            "detected_intent": intent,
            "retrieved_context": context,
            "task": "Generate a concise legal guidance explanation in plain language with next actions.",
            "constraints": "Do not fabricate laws. Use only retrieved context.",
        }

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal workflow assistant. Provide practical, procedural guidance.",
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        content = completion.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


def generate_response(query: str, processed_query: Dict, context: Dict, confidence_score: float) -> Dict:
    intent = processed_query.get("intent", "general_legal")
    primary = context.get("primary")

    if not primary:
        return {
            "query": query,
            "intent": intent,
            "matched_category": None,
            "matched_subcategory": None,
            "confidence_score": 0.0,
            "explanation": _local_explanation(query, intent, context, 0.0),
            "steps": [],
            "documents": [],
            "authorities": [],
            "suggestions": _local_suggestions(intent, 0.0, False),
            "alternatives": [],
        }

    llm_explanation = _try_openai_response(query, intent, context)
    explanation = llm_explanation or _local_explanation(query, intent, context, confidence_score)

    suggestions = _local_suggestions(
        intent=intent,
        confidence=confidence_score,
        has_alternatives=bool(context.get("alternatives")),
    )

    return {
        "query": query,
        "intent": intent,
        "matched_category": primary.get("category"),
        "matched_subcategory": primary.get("subcategory"),
        "confidence_score": round(float(confidence_score), 4),
        "explanation": explanation,
        "steps": primary.get("steps", []),
        "documents": primary.get("documents", []),
        "authorities": primary.get("authorities", []),
        "suggestions": suggestions,
        "alternatives": context.get("alternatives", []),
    }
