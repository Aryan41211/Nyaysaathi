"""Response validation and safety gating layer for NyaySaathi.

This module is the final guard before returning legal guidance.
It prevents unsafe guesses and ensures response shape is consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FALLBACK_MESSAGE = "I need more details to guide you correctly."


@dataclass
class ValidationResult:
    decision: str
    confidence: str
    answer: str
    disclaimer: str
    clarification_required: bool
    clarification_message: str
    clarification_questions: list[str]
    intent_match: bool
    structured: dict[str, Any]
    debug: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "answer": self.answer,
            "disclaimer": self.disclaimer,
            "clarification": {
                "required": self.clarification_required,
                "message": self.clarification_message,
                "questions": self.clarification_questions,
            },
            "intent_match": self.intent_match,
            "structured": self.structured,
            "debug": self.debug,
        }


def _normalize_confidence(value: str | None) -> str:
    conf = str(value or "Low").strip().lower()
    if conf in {"high", "medium", "low"}:
        return conf.capitalize()
    return "Low"


def _risk_disclaimer(intent: str, confidence: str) -> str:
    intent_l = str(intent or "").lower()
    if confidence == "High":
        return ""

    if any(k in intent_l for k in ["violence", "fir", "police", "fraud", "cyber"]):
        return (
            "This is procedural legal information, not final legal advice. "
            "For urgent risk, contact local police or emergency services immediately."
        )

    return (
        "This is procedural legal information based on available details and may need professional verification. "
        "Please consult a qualified advocate for final legal advice."
    )


def _intent_match_score(matched_intent: str, top_case: dict[str, Any], keywords: list[str]) -> float:
    top_blob = " ".join(
        [
            str(top_case.get("category", "")),
            str(top_case.get("subcategory", "")),
            str(top_case.get("problem_description", "")),
            " ".join(str(k) for k in (top_case.get("keywords") or []) if k),
        ]
    ).lower()

    intent_terms = [part.strip().lower() for part in str(matched_intent or "").split() if part.strip()]
    if not intent_terms and not keywords:
        return 0.0

    intent_hits = sum(1 for t in intent_terms if t in top_blob)
    keyword_hits = sum(1 for k in keywords if str(k).lower() in top_blob)

    term_score = intent_hits / max(1, len(intent_terms)) if intent_terms else 0.0
    keyword_score = keyword_hits / max(1, len(keywords)) if keywords else 0.0
    return max(0.0, min(1.0, (0.70 * term_score) + (0.30 * keyword_score)))


def _structured_payload(top_case: dict[str, Any], fallback_answer: str) -> dict[str, Any]:
    steps = list(top_case.get("workflow_steps") or top_case.get("workflow") or [])
    documents = list(top_case.get("required_documents") or top_case.get("documents_required") or [])
    authorities = list(top_case.get("authorities") or [])

    if not steps and fallback_answer:
        steps = [fallback_answer]

    return {
        "actions": steps,
        "required_documents": documents,
        "where_to_go": authorities,
        "optional_tips": [
            "Keep copies of all submissions and acknowledgments.",
            "Record dates and names of officials you interact with.",
        ],
    }


def validate_response(query: str, results: list[dict[str, Any]], nlp_meta: dict[str, Any]) -> ValidationResult:
    """Validate retrieved guidance and enforce safe response gating."""
    del query

    top = results[0] if results else {}
    matched_intent = str((nlp_meta or {}).get("matched_intent") or "General legal issue")
    confidence = _normalize_confidence((nlp_meta or {}).get("confidence"))
    keywords = list((nlp_meta or {}).get("keywords") or [])

    similarity_score = float(top.get("similarity_score") or 0.0)
    intent_score = _intent_match_score(matched_intent=matched_intent, top_case=top, keywords=keywords)

    top_margin = float(((nlp_meta or {}).get("reasoning_signals") or {}).get("top_margin") or 0.0)
    query_clarity = float(((nlp_meta or {}).get("reasoning_signals") or {}).get("query_clarity") or 0.0)

    no_strong_match = (not results) or (similarity_score < 0.46)
    intent_mismatch = intent_score < 0.35
    ambiguous = bool((nlp_meta or {}).get("clarification_required", False)) or query_clarity < 0.40 or top_margin < 0.03

    # Hard safety gate: avoid guidance when retrieval is weak or mismatch is likely.
    if confidence == "Low" or no_strong_match or intent_mismatch or ambiguous:
        clarification_questions = list((nlp_meta or {}).get("clarification_questions") or [])
        if not clarification_questions:
            clarification_questions = [
                "Who is the opposite party in this issue?",
                "What exactly happened and when?",
                "Which documents or proof do you currently have?",
            ]

        return ValidationResult(
            decision="clarification_only",
            confidence="Low",
            answer=FALLBACK_MESSAGE,
            disclaimer="",
            clarification_required=True,
            clarification_message=str((nlp_meta or {}).get("clarification_message") or FALLBACK_MESSAGE),
            clarification_questions=clarification_questions,
            intent_match=False,
            structured={
                "actions": [],
                "required_documents": [],
                "where_to_go": [],
                "optional_tips": [],
            },
            debug={
                "intent_score": round(intent_score, 4),
                "similarity_score": round(similarity_score, 4),
                "top_margin": round(top_margin, 4),
                "query_clarity": round(query_clarity, 4),
                "gate_reason": "low_confidence_or_ambiguity",
            },
        )

    workflow_steps = list(top.get("workflow_steps") or top.get("workflow") or [])
    answer = workflow_steps[0] if workflow_steps else str(top.get("problem_description") or "Relevant legal workflow identified.")
    disclaimer = _risk_disclaimer(matched_intent, confidence)

    decision = "answer"
    if confidence == "Medium":
        decision = "answer_with_disclaimer"

    return ValidationResult(
        decision=decision,
        confidence=confidence,
        answer=answer,
        disclaimer=disclaimer,
        clarification_required=False,
        clarification_message="",
        clarification_questions=[],
        intent_match=True,
        structured=_structured_payload(top_case=top, fallback_answer=answer),
        debug={
            "intent_score": round(intent_score, 4),
            "similarity_score": round(similarity_score, 4),
            "top_margin": round(top_margin, 4),
            "query_clarity": round(query_clarity, 4),
            "gate_reason": "passed",
        },
    )
