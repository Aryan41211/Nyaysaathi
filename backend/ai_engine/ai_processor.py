"""Main AI pipeline for NyaySaathi legal guidance."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from legal_cases import services
from legal_cases.nlp_processor import build_enhanced_search_string, process_query as process_nlp_query
from services.workflow_service import get_workflow, localize_case_payload, resolve_category_id

from .classifier import classify_legal_problem
from .language_detector import detect_language
from .normalizer import normalize_user_input
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


def _build_understanding(raw_query: str) -> tuple[str, dict[str, Any], bool]:
    """Build search-ready query understanding with AI-first fallback semantics.

    Returns:
        (classification_query, nlp_meta, used_ai_understanding)
    """
    nlp_meta = process_nlp_query(raw_query)
    search_ready = str(nlp_meta.get("search_ready_query", "")).strip()
    if search_ready:
        query_for_classification = build_enhanced_search_string(nlp_meta, raw_query)
    else:
        query_for_classification = raw_query
    used_ai = str(nlp_meta.get("nlp_source", "")).strip().lower() == "claude"
    return query_for_classification, nlp_meta, used_ai


def _normalize_nlp_meta(nlp_meta: dict[str, Any], fallback_query: str) -> dict[str, Any]:
    """Normalize NLP metadata shape consumed by frontend and API clients."""
    payload = dict(nlp_meta or {})
    understood = str(payload.get("search_ready_query", "")).strip() or str(fallback_query or "").strip()
    payload["understood_as"] = understood

    confidence = str(payload.get("confidence", "Low")).strip().lower()
    payload["confidence"] = confidence.capitalize() if confidence else "Low"
    return payload


def _is_low_confidence(nlp_meta: dict[str, Any]) -> bool:
    confidence = str(nlp_meta.get("confidence", "")).strip().lower()
    return confidence in LOW_CONFIDENCE_LABELS


def _build_clarification_questions(nlp_meta: dict[str, Any]) -> list[str]:
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
    understood_query, nlp_meta, used_ai_understanding = _build_understanding(query)
    nlp_meta = _normalize_nlp_meta(nlp_meta, fallback_query=understood_query)
    if used_ai_understanding:
        ai_calls += 1

    detected_language = detect_language(query)
    if detected_language not in SUPPORTED_LANGUAGES:
        detected_language = DEFAULT_LANGUAGE

    normalized_query, normalized_language, used_ai_normalizer = normalize_user_input(
        understood_query,
        preferred_language=detected_language,
        allow_ai=True,
    )
    if used_ai_normalizer:
        ai_calls += 1
    if normalized_language in SUPPORTED_LANGUAGES:
        detected_language = normalized_language

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

    if not category_id:
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
            "clarification_message": "We need a few details before showing accurate legal workflow guidance.",
            "clarification_questions": clarification_questions,
            "ai_understanding": {
                "source": nlp_meta.get("nlp_source", "fallback"),
                "understood_as": nlp_meta.get("search_ready_query", normalized_query),
                "keywords": nlp_meta.get("keywords", []),
                "confidence": nlp_meta.get("confidence", "Low"),
                "detected_language": nlp_meta.get("detected_language", detected_language),
            },
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
        "clarification_required": low_confidence,
        "clarification_message": (
            "Best match shown with low confidence. Please answer clarification questions for a more precise workflow."
            if low_confidence
            else ""
        ),
        "clarification_questions": clarification_questions,
        "ai_understanding": {
            "source": nlp_meta.get("nlp_source", "fallback"),
            "understood_as": nlp_meta.get("search_ready_query", normalized_query),
            "keywords": nlp_meta.get("keywords", []),
            "confidence": nlp_meta.get("confidence", "Low"),
            "detected_language": nlp_meta.get("detected_language", detected_language),
        },
        "semantic_match": {
            "grounded": True,
            "grounding_source": "database_only",
            "category_id": category_id,
        },
        "total": 1,
        "message": "Guidance generated successfully.",
        "data": [localized_case],
    }
