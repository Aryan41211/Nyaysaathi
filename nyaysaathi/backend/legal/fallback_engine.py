"""Fallback and clarification logic for resilient legal understanding."""

from __future__ import annotations

from typing import Any, Final

LEGAL_SIGNAL_TERMS: Final[tuple[str, ...]] = (
    "fir",
    "complaint",
    "police",
    "court",
    "notice",
    "salary",
    "wage",
    "tenant",
    "landlord",
    "property",
    "divorce",
    "maintenance",
    "fraud",
    "cyber",
    "harassment",
    "refund",
    "consumer",
    "agreement",
    "contract",
    "loan",
    "pan",
    "aadhar",
)

NON_LEGAL_MARKERS: Final[tuple[str, ...]] = (
    "weather",
    "recipe",
    "movie",
    "song",
    "game",
    "joke",
    "travel plan",
    "gym",
    "diet",
)

DEFAULT_RESULT: Final[dict[str, Any]] = {
    "intent": "unknown_legal_intent",
    "category": "Other",
    "subcategory": "General",
    "summary": "Unable to reliably determine the legal issue from the provided input.",
    "next_action_type": "clarify_first",
    "confidence": 0.25,
    "is_legal": False,
    "clarification_required": True,
    "clarification_questions": ["Could you share what legal issue you are facing and what outcome you want?"],
    "additional_issues": [],
}


class FallbackEngine:
    """Encapsulates non-legal detection, fallback classification, and clarifications."""

    @staticmethod
    def is_probably_non_legal_input(user_input: str) -> bool:
        """Heuristic guard for clearly non-legal or very weak prompts."""
        text = (user_input or "").lower().strip()
        if len(text) < 6:
            return True
        if any(term in text for term in LEGAL_SIGNAL_TERMS):
            return False
        return any(marker in text for marker in NON_LEGAL_MARKERS)

    @staticmethod
    def generate_clarification_questions(result: dict[str, Any], user_input: str) -> list[str]:
        """Generate focused follow-up questions when confidence is low or details are missing."""
        questions: list[str] = list(result.get("clarification_questions") or [])
        if questions:
            return questions[:3]

        text = (user_input or "").strip()
        if not text:
            return ["Could you describe your legal issue and what help you need?"]

        return [
            "What exactly happened and when did it happen?",
            "Who is involved (person, company, landlord, employer, or authority)?",
            "What outcome are you seeking (refund, FIR, notice, compensation, etc.)?",
        ]

    @staticmethod
    def apply_fallback_rules(result: dict[str, Any], user_input: str) -> dict[str, Any]:
        """Apply fallback classification and clarification policy to normalized output."""
        if result.get("clarification_required") and not result.get("clarification_questions"):
            result["clarification_questions"] = FallbackEngine.generate_clarification_questions(result, user_input)

        if FallbackEngine.is_probably_non_legal_input(user_input):
            result["is_legal"] = False
            result["category"] = "Other"
            result["subcategory"] = "General"
            result["next_action_type"] = "clarify_first"
            result["clarification_required"] = True
            result["clarification_questions"] = [
                "Could you describe the legal issue or dispute you need help with?"
            ]

        if float(result.get("confidence", 0.25)) < 0.55:
            result["clarification_required"] = True
            if not result.get("clarification_questions"):
                result["clarification_questions"] = FallbackEngine.generate_clarification_questions(result, user_input)

        return result

    @staticmethod
    def build_error_fallback(user_input: str) -> dict[str, Any]:
        """Create safe fallback object for model/parsing/runtime failures."""
        result = dict(DEFAULT_RESULT)
        result["summary"] = user_input[:280] if user_input else result["summary"]
        result["clarification_questions"] = FallbackEngine.generate_clarification_questions(result, user_input)
        return result


def attach_legacy_aliases(result: dict[str, Any]) -> dict[str, Any]:
    """Attach compatibility keys consumed by existing API layer."""
    output = dict(result)
    output["intent_summary"] = output.get("summary", "")
    output["legal_category"] = output.get("category", "Other")
    output["sub_category"] = output.get("subcategory", "General")
    output["confidence_score"] = output.get("confidence", 0.25)
    return output
