"""Main AI pipeline for NyaySaathi legal guidance."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from legal_cases import services
from services.workflow_service import get_workflow, localize_case_payload, resolve_category_id

from .classifier import classify_legal_problem
from .language_detector import detect_language
from .normalizer import normalize_user_input
from .translator import translate_workflow

logger = logging.getLogger(__name__)


MAX_AI_CALLS_PER_REQUEST = 2


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
    detected_language = detect_language(query)
    if detected_language not in SUPPORTED_LANGUAGES:
        detected_language = DEFAULT_LANGUAGE

    normalized_query, normalized_language, used_ai_normalizer = normalize_user_input(
        query,
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
            "message": "No matching workflow found. Please provide more details.",
            "classification": class_meta,
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
        "total": 1,
        "message": "Guidance generated successfully.",
        "data": [localized_case],
    }
