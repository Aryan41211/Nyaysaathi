"""Fallback classification for weak semantic similarity cases."""

from __future__ import annotations

from typing import Any

KEYWORD_CATEGORY: dict[str, str] = {
    "salary": "LABOUR",
    "wage": "LABOUR",
    "payment": "LABOUR",
    "employer": "LABOUR",
    "fraud": "CYBER",
    "scam": "CYBER",
    "upi": "CYBER",
    "hacked": "CYBER",
    "bank": "CYBER",
    "landlord": "PROPERTY",
    "tenant": "PROPERTY",
    "deposit": "PROPERTY",
    "rent": "PROPERTY",
    "property": "PROPERTY",
}


class FallbackEngine:
    """Simple dictionary-based fallback category classification."""

    @staticmethod
    def classify(user_input: str) -> dict[str, Any]:
        text = (user_input or "").lower().strip()
        if not text:
            return {
                "category": "Unknown",
                "confidence": "Low",
                "similarity_score": 0.0,
                "matched_text": "",
                "source": "fallback",
                "message": "Please describe your issue",
            }

        for token, category in KEYWORD_CATEGORY.items():
            if token in text:
                return {
                    "category": category,
                    "confidence": "Low",
                    "similarity_score": 0.0,
                    "matched_text": f"keyword:{token}",
                    "source": "fallback",
                }

        return {
            "category": "Unknown",
            "confidence": "Low",
            "similarity_score": 0.0,
            "matched_text": "",
            "source": "fallback",
        }

    @staticmethod
    def build_error_fallback(user_input: str) -> dict[str, Any]:
        """Compatibility wrapper for older callers."""
        return FallbackEngine.classify(user_input)


def attach_legacy_aliases(result: dict[str, Any]) -> dict[str, Any]:
    """Keep compatibility aliases consumed by existing APIs."""
    payload = dict(result)
    payload["intent_summary"] = payload.get("matched_text", "")
    payload["legal_category"] = payload.get("category", "Unknown")
    payload["sub_category"] = payload.get("subcategory", "General")
    payload["confidence_score"] = payload.get("similarity_score", 0.0)
    return payload
