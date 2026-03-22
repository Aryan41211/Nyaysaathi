"""High-accuracy local semantic classifier for NyaySaathi legal intent understanding."""

from __future__ import annotations

from typing import Any

from .embedding_engine import get_embedding_store, get_user_embedding
from .fallback_engine import FallbackEngine, attach_legacy_aliases
from .intent_engine import IntentEngine
from .monitoring import AIMonitor
from .preprocessing import clean_text
from .settings import FALLBACK_SIMILARITY_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD, MEDIUM_CONFIDENCE_THRESHOLD
from .similarity_engine import find_best_match
from .workflow_mapper import build_explanation, get_clarification_questions, get_workflow

_AI_MONITOR = AIMonitor(snapshot_every=25)


def _confidence_from_similarity(similarity: float) -> str:
    if similarity >= HIGH_CONFIDENCE_THRESHOLD:
        return "High"
    if similarity >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "Medium"
    if similarity >= FALLBACK_SIMILARITY_THRESHOLD:
        return "Low"
    return "Low"


def _embedding_response(user_input: str, match: dict[str, Any]) -> dict[str, Any]:
    similarity = float(match.get("similarity", 0.0))
    category = str(match.get("category", "Unknown"))
    matched_text = str(match.get("matched_text", ""))
    confidence = _confidence_from_similarity(similarity)

    clarification_questions: list[str] = []
    if confidence in {"Medium", "Low"}:
        clarification_questions = get_clarification_questions(category)

    return {
        "intent": IntentEngine.detect_intent(user_input),
        "category": category,
        "matched_text": matched_text,
        "matched_problem": matched_text,
        "confidence": confidence,
        "similarity_score": round(similarity, 4),
        "workflow_steps": get_workflow(category),
        "explanation": build_explanation(category, matched_text),
        "clarification_questions": clarification_questions,
        "problem_summary": matched_text,
        "source": "embedding",
    }


def understand_user_problem(user_input: str) -> dict[str, Any]:
    """Classify legal problem via local semantic similarity with fallback routing."""
    normalized = clean_text(user_input)
    if not normalized:
        response = {
            "intent": "guidance",
            "category": "Unknown",
            "matched_text": "",
            "matched_problem": "",
            "confidence": "Low",
            "similarity_score": 0.0,
            "workflow_steps": ["Please describe problem more clearly"],
            "explanation": "This issue is classified as Unknown because details are insufficient.",
            "clarification_questions": [
                "Can you share more details about the legal issue?",
                "Who is involved and what outcome do you want?",
            ],
            "problem_summary": "",
            "source": "fallback",
            "message": "Please describe your issue",
        }
        return attach_legacy_aliases(response)

    try:
        store = get_embedding_store()
        user_embedding = get_user_embedding(normalized)
        match = find_best_match(user_embedding, store)

        similarity = float(match.get("similarity", 0.0))
        if similarity < FALLBACK_SIMILARITY_THRESHOLD:
            fallback = FallbackEngine.classify(normalized)
            fallback["intent"] = IntentEngine.detect_intent(normalized)
            fallback["matched_problem"] = fallback.get("matched_text", "")
            fallback["workflow_steps"] = get_workflow(fallback.get("category", "Unknown"))
            fallback["explanation"] = build_explanation(
                fallback.get("category", "Unknown"),
                fallback.get("matched_text", ""),
            )
            fallback["clarification_questions"] = get_clarification_questions(
                fallback.get("category", "Unknown")
            )
            fallback["problem_summary"] = fallback.get("matched_text", "")
            _AI_MONITOR.record_fallback(error_type="low_similarity", retries_used=0, latency_ms=0.0)
            return attach_legacy_aliases(fallback)

        result = _embedding_response(normalized, match)
        _AI_MONITOR.record_success(
            category=result["category"],
            confidence=float(result["similarity_score"]),
            clarification_required=False,
            retries_used=0,
            latency_ms=0.0,
        )
        return attach_legacy_aliases(result)
    except Exception:  # noqa: BLE001
        fallback = FallbackEngine.classify(normalized)
        fallback["intent"] = IntentEngine.detect_intent(normalized)
        fallback["matched_problem"] = fallback.get("matched_text", "")
        fallback["workflow_steps"] = get_workflow(fallback.get("category", "Unknown"))
        fallback["explanation"] = build_explanation(
            fallback.get("category", "Unknown"),
            fallback.get("matched_text", ""),
        )
        fallback["clarification_questions"] = get_clarification_questions(
            fallback.get("category", "Unknown")
        )
        fallback["problem_summary"] = fallback.get("matched_text", "")
        _AI_MONITOR.record_fallback(error_type="embedding_error", retries_used=0, latency_ms=0.0)
        return attach_legacy_aliases(fallback)


def get_example_test_inputs() -> list[str]:
    """Return manual test prompts for classifier smoke testing."""
    return [
        "My company has not paid salary",
        "UPI fraud happened",
        "Landlord keeping my deposit",
        "Employer delayed payment",
        "Bank account hacked",
    ]


def get_ai_monitoring_snapshot() -> dict[str, Any]:
    """Return in-process AI monitor snapshot."""
    return _AI_MONITOR.snapshot()
