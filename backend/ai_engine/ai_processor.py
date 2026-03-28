"""Main AI pipeline for NyaySaathi legal guidance."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from legal_cases import services
from legal_cases.response_validator import validate_response
from services.workflow_service import get_workflow, localize_case_payload, resolve_category_id
from search.query_processor import process_query as preprocess_query

from .classifier import classify_legal_problem
from .language_detector import detect_language
from .translator import translate_workflow

logger = logging.getLogger(__name__)


MAX_AI_CALLS_PER_REQUEST = 2
LOW_CONFIDENCE_LABELS = {"low", "unknown", ""}


def _legacy_classifier(query: str) -> str:
    results, _ = services.search_cases(query, top_k=1)
    if not results:
        return ""
    top = results[0]
    return resolve_category_id(
        str(top.get("subcategory", "")),
        str(top.get("category", "")),
        query,
    )


def _build_understanding(raw_query: str) -> tuple[str, list[dict[str, Any]], dict[str, Any], bool]:
    """Build understanding from deterministic local NLP pipeline + semantic intent layer."""
    processed = preprocess_query(raw_query)
    semantic_results, semantic_meta = services.search_cases(raw_query, top_k=3)

    nlp_meta = dict(semantic_meta or {})
    nlp_meta.setdefault("detected_language", processed.language)
    nlp_meta.setdefault("normalized_query", processed.normalized)
    nlp_meta.setdefault("search_ready_query", processed.expanded)
    nlp_meta.setdefault("keywords", processed.keywords)
    nlp_meta.setdefault("problem_domain", "Unknown")
    nlp_meta.setdefault("problem_type", "General")
    nlp_meta.setdefault("likely_authority", "District Legal Services Authority")
    nlp_meta.setdefault("matched_intent", "General legal issue")
    nlp_meta.setdefault("confidence", processed.confidence_hint)
    nlp_meta.setdefault("ambiguity_score", processed.ambiguity_score)
    nlp_meta.setdefault("reasoning_signals", processed.debug_signals)

    used_ai = str(nlp_meta.get("nlp_source", "")).strip().lower() in {"claude", "llm"}
    return processed.expanded or raw_query, semantic_results, nlp_meta, used_ai


def _normalize_nlp_meta(nlp_meta: dict[str, Any], fallback_query: str) -> dict[str, Any]:
    """Normalize NLP metadata shape consumed by frontend and API clients."""
    payload = dict(nlp_meta or {})
    understood = str(payload.get("search_ready_query", "")).strip() or str(fallback_query or "").strip()
    payload["understood_as"] = understood

    confidence = str(payload.get("confidence", "Low")).strip().lower()
    payload["confidence"] = confidence.capitalize() if confidence else "Low"
    payload.setdefault("clarification_required", payload["confidence"].lower() == "low")
    payload.setdefault("clarification_questions", [])
    payload.setdefault("clarification_message", "")
    return payload


def _is_low_confidence(nlp_meta: dict[str, Any]) -> bool:
    if bool(nlp_meta.get("clarification_required")):
        return True
    confidence = str(nlp_meta.get("confidence", "")).strip().lower()
    if confidence in LOW_CONFIDENCE_LABELS:
        return True
    score = float(nlp_meta.get("overall_confidence_score") or 0.0)
    return score > 0 and score < 0.52


def _build_clarification_questions(nlp_meta: dict[str, Any]) -> list[str]:
    model_questions = [str(q).strip() for q in list(nlp_meta.get("clarification_questions") or []) if str(q).strip()]
    if model_questions:
        return model_questions[:4]

    text = " ".join(
        [
            str(nlp_meta.get("search_ready_query", "")),
            " ".join(str(k) for k in nlp_meta.get("keywords", []) if k),
        ]
    ).lower()

    if any(t in text for t in ["salary", "wage", "employer", "labour"]):
        return [
            "Is this a salary delay, partial salary payment, or complete non-payment?",
            "Are you employed in private job, contract work, or daily wage work?",
            "For how many months is payment pending and do you have salary proof (slips/bank statement)?",
        ]

    if any(t in text for t in ["landlord", "tenant", "deposit", "rent", "house"]):
        return [
            "Is the issue about rent, eviction, or refund of security deposit?",
            "Do you have rent agreement and payment receipts?",
            "How long has this dispute been pending?",
        ]

    if any(t in text for t in ["fraud", "upi", "scam", "cyber", "bank"]):
        return [
            "Was this UPI fraud, card fraud, or social media/OTP scam?",
            "When did the transaction happen and what amount was involved?",
            "Do you have transaction ID, screenshots, and complaint reference number?",
        ]

    if any(t in text for t in ["police", "fir", "complaint"]):
        return [
            "Is the issue about FIR not being registered, delayed action, or harassment?",
            "Which police station did you approach and on what date?",
            "Do you have written complaint copy or acknowledgment?",
        ]

    return [
        "What is the main legal issue in one line?",
        "Who is the opposite party (employer, landlord, police, bank, neighbor, etc.)?",
        "What action have you already taken and when?",
    ]


def _resolve_category_from_semantic_candidates(results: list[dict[str, Any]], query: str) -> str:
    if not results:
        return ""

    top = results[0]
    return resolve_category_id(
        str(top.get("subcategory", "")),
        str(top.get("category", "")),
        query,
    )


def generate_legal_guidance(user_input: str) -> dict[str, Any]:
    """
    Production-safe pipeline:
      normalize -> detect language -> classify -> retrieve dataset workflow -> translate if needed.
    """
    request_id = str(uuid4())
    query = (user_input or "").strip()

    if not query:
        return {
            "request_id": request_id,
            "query": "",
            "language": "en",
            "category": "",
            "category_id": "",
            "workflow": [],
            "workflow_steps": [],
            "documents_required": [],
            "authorities": [],
            "complaint_template": "",
            "total": 0,
            "message": "Please provide a legal query.",
        }

    ai_calls = 0
    understood_query, semantic_candidates, nlp_meta, used_ai_understanding = _build_understanding(query)
    nlp_meta = _normalize_nlp_meta(nlp_meta, fallback_query=understood_query)
    if used_ai_understanding:
        ai_calls += 1

    detected_language = str(nlp_meta.get("detected_language", "")).strip() or detect_language(query)
    if detected_language not in SUPPORTED_LANGUAGES:
        detected_language = DEFAULT_LANGUAGE

    normalized_query = str(nlp_meta.get("search_ready_query", "")).strip() or understood_query

    category_id = _resolve_category_from_semantic_candidates(semantic_candidates, normalized_query)
    class_meta: dict[str, Any] = {
        "source": "semantic_intent_layer" if category_id else "none",
        "used_ai": False,
    }

    if not category_id:
        allow_ai_classification = ai_calls < MAX_AI_CALLS_PER_REQUEST
        category_id, class_meta = classify_legal_problem(
            normalized_query,
            original_text=query,
            allow_ai=allow_ai_classification,
            legacy_fallback=_legacy_classifier,
        )
        if class_meta.get("used_ai"):
            ai_calls += 1

    low_confidence = _is_low_confidence(nlp_meta)
    clarification_questions = _build_clarification_questions(nlp_meta) if low_confidence else []

    if low_confidence or not category_id:
        return {
            "request_id": request_id,
            "query": query,
            "language": detected_language,
            "category": "",
            "category_id": "",
            "workflow": [],
            "workflow_steps": [],
            "documents_required": [],
            "authorities": [],
            "complaint_template": "",
            "detected_language": detected_language,
            "normalized_query": normalized_query,
            "translation_triggered": False,
            "cache_hit": False,
            "total": 0,
            "message": "Low confidence understanding. Please answer clarification questions to improve the match.",
            "classification": class_meta,
            "nlp": nlp_meta,
            "clarification_required": True,
            "clarification_message": (
                str(nlp_meta.get("clarification_message", "")).strip()
                or "We need a few details before showing accurate legal workflow guidance."
            ),
            "clarification_questions": clarification_questions,
            "ai_understanding": {
                "source": nlp_meta.get("nlp_source", "fallback"),
                "understood_as": nlp_meta.get("search_ready_query", normalized_query),
                "keywords": nlp_meta.get("keywords", []),
                "confidence": nlp_meta.get("confidence", "Low"),
                "detected_language": nlp_meta.get("detected_language", detected_language),
            },
            "reasoning_signals": nlp_meta.get("reasoning_signals", {}),
            "data": [],
        }

    localized_workflow = get_workflow(category_id, detected_language)
    english_workflow = get_workflow(category_id, DEFAULT_LANGUAGE)
    selected_workflow = localized_workflow or english_workflow

    if not selected_workflow:
        return {
            "request_id": request_id,
            "query": query,
            "language": DEFAULT_LANGUAGE,
            "category": "",
            "category_id": category_id,
            "workflow": [],
            "workflow_steps": [],
            "documents_required": [],
            "authorities": [],
            "complaint_template": "",
            "detected_language": detected_language,
            "normalized_query": normalized_query,
            "translation_triggered": False,
            "cache_hit": False,
            "total": 0,
            "message": "Workflow data unavailable for this category.",
            "classification": class_meta,
            "data": [],
        }

    workflow_steps = list(selected_workflow.get("workflow_steps") or [])
    translation_triggered = False
    cache_hit = False

    if (
        detected_language != DEFAULT_LANGUAGE
        and not localized_workflow
        and english_workflow
        and ai_calls < MAX_AI_CALLS_PER_REQUEST
    ):
        translated_steps, translation_triggered, cache_hit = translate_workflow(
            workflow_text=list(english_workflow.get("workflow_steps") or []),
            target_language=detected_language,
            category=str(english_workflow.get("category", "Unknown")),
            request_id=request_id,
        )
        workflow_steps = translated_steps or workflow_steps
        if translation_triggered:
            ai_calls += 1

    case_payload = {
        "category": selected_workflow.get("category", ""),
        "subcategory": selected_workflow.get("subcategory", ""),
        "problem_description": selected_workflow.get("problem_description", ""),
        "workflow_steps": workflow_steps,
        "documents_required": list(selected_workflow.get("documents_required") or []),
        "required_documents": list(selected_workflow.get("documents_required") or []),
        "authorities": list(selected_workflow.get("authorities") or []),
        "complaint_template": selected_workflow.get("complaint_template", ""),
    }
    localized_case = localize_case_payload(case_payload, detected_language)

    safety_payload = validate_response(
        query=query,
        results=[localized_case],
        nlp_meta=nlp_meta,
    ).to_dict()
    if str(safety_payload.get("decision") or "").lower() == "clarification_only":
        clarification = dict(safety_payload.get("clarification") or {})
        return {
            "request_id": request_id,
            "query": query,
            "language": detected_language,
            "category": "",
            "category_id": category_id,
            "workflow": [],
            "workflow_steps": [],
            "documents_required": [],
            "authorities": [],
            "complaint_template": "",
            "detected_language": detected_language,
            "normalized_query": normalized_query,
            "translation_triggered": translation_triggered,
            "cache_hit": cache_hit,
            "classification": class_meta,
            "nlp": nlp_meta,
            "clarification_required": True,
            "clarification_message": str(clarification.get("message") or "I need more details to guide you correctly."),
            "clarification_questions": list(clarification.get("questions") or []),
            "reasoning_signals": nlp_meta.get("reasoning_signals", {}),
            "semantic_match": {
                "grounded": True,
                "grounding_source": "database_only",
                "category_id": category_id,
            },
            "safety": safety_payload,
            "total": 0,
            "message": "More details required for safe legal guidance.",
            "data": [],
        }

    return {
        "request_id": request_id,
        "query": query,
        "language": detected_language,
        "detected_language": detected_language,
        "normalized_query": normalized_query,
        "category_id": category_id,
        "category": localized_case.get("category", selected_workflow.get("category", "")),
        "subcategory": localized_case.get("subcategory", selected_workflow.get("subcategory", "")),
        "workflow": workflow_steps,
        "workflow_steps": workflow_steps,
        "localized_workflow": workflow_steps,
        "workflow_english": list((english_workflow or {}).get("workflow_steps") or workflow_steps),
        "documents_required": list(localized_case.get("documents_required") or []),
        "required_documents": list(localized_case.get("documents_required") or []),
        "authorities": list(localized_case.get("authorities") or []),
        "complaint_template": localized_case.get("complaint_template", ""),
        "translation_triggered": translation_triggered,
        "cache_hit": cache_hit,
        "classification": class_meta,
        "nlp": nlp_meta,
        "clarification_required": False,
        "clarification_message": "",
        "clarification_questions": [],
        "ai_understanding": {
            "source": nlp_meta.get("nlp_source", "fallback"),
            "understood_as": nlp_meta.get("search_ready_query", normalized_query),
            "keywords": nlp_meta.get("keywords", []),
            "confidence": nlp_meta.get("confidence", "Low"),
            "detected_language": nlp_meta.get("detected_language", detected_language),
        },
        "reasoning_signals": nlp_meta.get("reasoning_signals", {}),
        "semantic_match": {
            "grounded": True,
            "grounding_source": "database_only",
            "category_id": category_id,
        },
        "safety": safety_payload,
        "total": 1,
        "message": "Guidance generated successfully.",
        "data": [localized_case],
    }
