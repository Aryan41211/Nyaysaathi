"""End-to-end multilingual legal guidance response generator."""

from __future__ import annotations

import logging
import os
from uuid import uuid4
from typing import Any

from django.conf import settings
from config import DEFAULT_LANGUAGE
from legal.ai_engine import understand_user_problem
from legal_cases import services
from services.workflow_service import get_workflow, localize_case_payload, resolve_category_id

from .language_detector import SUPPORTED_LANGUAGES, detect_language
from .preprocessing import preprocess_text
from .roman_normalizer import normalize_text
from .semantic_search import find_best_category
from .translator import translate_workflow

logger = logging.getLogger(__name__)


def _openai_available() -> bool:
    api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "")
    return bool(api_key)


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.50:
        return "Medium"
    return "Low"


def generate_legal_guidance(user_input: str) -> dict[str, Any]:
    """
    Generate multilingual legal guidance without changing existing retrieval architecture.

    Pipeline:
      User Input -> Language Detection -> Roman Normalization -> Existing Intent Classification
      -> Existing Workflow Retrieval -> Translation Layer -> Localized Response
    """
    request_id = str(uuid4())

    query = (user_input or "").strip()
    if not query:
        return {
            "request_id": request_id,
            "query": "",
            "detected_language": "en",
            "normalized_query": "",
            "data": [],
            "category_id": "",
            "category": "",
            "subcategory": "",
            "workflow": [],
            "localized_workflow": [],
            "documents_required": [],
            "authorities": [],
            "complaint_template": "",
            "translation_triggered": False,
            "total": 0,
            "message": "Please provide a legal query.",
            "nlp": {
                "detected_language": "en",
                "understood_as": "",
                "keywords": [],
                "confidence": "Low",
                "nlp_source": "input_validation",
            },
            "ai_understanding": {},
        }
    try:
        detected_language = detect_language(query)
        if detected_language not in SUPPORTED_LANGUAGES:
            detected_language = "en"

        normalized_query = preprocess_text(query, language=detected_language)
        semantic_match = find_best_category(normalized_query)

        ai_result: dict[str, Any]
        if _openai_available():
            ai_result = understand_user_problem(normalized_query)
        else:
            # Keep architecture stable while avoiding unnecessary OpenAI calls.
            ai_result = {
                "intent": "semantic_fallback",
                "legal_category": "",
                "sub_category": "",
                "confidence_score": 0.0,
                "summary": normalized_query[:280],
            }

        semantic_category = str(semantic_match.get("category") or "").strip()
        legal_category = semantic_category or str(ai_result.get("legal_category") or ai_result.get("category") or "").strip()
        sub_category = str(ai_result.get("sub_category") or ai_result.get("subcategory") or "").strip()
        confidence_score = float(ai_result.get("confidence_score", ai_result.get("confidence", 0.0)) or 0.0)

        # Keep existing retrieval logic unchanged.
        category_cases = services.get_all_cases(category=legal_category) if legal_category else []
        if category_cases:
            results = category_cases[:5]
            nlp_meta = {
                "detected_language": detected_language,
                "normalized_query": normalized_query,
                "search_ready_query": normalized_query,
                "keywords": [],
                "confidence": _confidence_label(confidence_score),
                "nlp_source": f"semantic_{semantic_match.get('source', 'none')}",
            }
        else:
            results, nlp_meta = services.search_cases(normalized_query, top_k=5)
            nlp_meta["detected_language"] = detected_language
            nlp_meta["normalized_query"] = nlp_meta.get("normalized_query") or normalized_query

        matched_subcategory = sub_category or (results[0].get("subcategory") if results else "")
        if (not legal_category or legal_category.lower() == "other") and results:
            legal_category = str(results[0].get("category") or legal_category or "").strip()
        if not matched_subcategory and results:
            matched_subcategory = str(results[0].get("subcategory") or "").strip()

        category_id = resolve_category_id(matched_subcategory, legal_category, normalized_query, query)

        localized_results = [localize_case_payload(case, detected_language) for case in results]

        localized_primary = get_workflow(category_id, detected_language) if category_id else None
        english_primary = get_workflow(category_id, DEFAULT_LANGUAGE) if category_id else None

        if localized_primary:
            localized_workflow = list(localized_primary.get("workflow_steps") or [])
            workflow_steps = list((english_primary or {}).get("workflow_steps") or localized_workflow)
            translation_triggered = False
            cache_hit = False
            response_language = str(localized_primary.get("language") or detected_language)
            legal_category = str(localized_primary.get("category") or legal_category or "").strip()
            matched_subcategory = str(localized_primary.get("subcategory") or matched_subcategory or "").strip()
            documents_required = list(localized_primary.get("documents_required") or [])
            authorities = list(localized_primary.get("authorities") or [])
            complaint_template = str(localized_primary.get("complaint_template") or "")
        else:
            workflow_steps = (results[0].get("workflow_steps") if results else []) or []
            localized_workflow, translation_triggered, cache_hit = translate_workflow(
                workflow_text=list(workflow_steps),
                target_language=detected_language,
                category=legal_category or matched_subcategory or "Unknown",
                request_id=request_id,
            )
            response_language = detected_language
            documents_required = list((results[0].get("required_documents") if results else []) or [])
            authorities = list((results[0].get("authorities") if results else []) or [])
            complaint_template = str((results[0].get("complaint_template") if results else "") or "")

        logger.info(
            "Guidance generated | request_id=%s language=%s category=%s translation_triggered=%s cache_hit=%s",
            request_id,
            detected_language,
            legal_category or "Unknown",
            translation_triggered,
            cache_hit,
        )

        message = (
            "Here is the procedural guidance for your problem."
            if results else
            "No matching cases found. Please describe your problem differently or browse categories."
        )

        return {
            "request_id": request_id,
            "query": query,
            "language": response_language,
            "detected_language": detected_language,
            "normalized_query": normalized_query,
            "nlp": {
                "detected_language": nlp_meta.get("detected_language", detected_language),
                "understood_as": nlp_meta.get("normalized_query") or nlp_meta.get("search_ready_query", normalized_query),
                "keywords": nlp_meta.get("keywords", []),
                "confidence": nlp_meta.get("confidence", "Low"),
                "nlp_source": nlp_meta.get("nlp_source", "fallback"),
            },
            "ai_understanding": ai_result,
            "semantic_match": semantic_match,
            "data": localized_results,
            "category_id": category_id,
            "category": legal_category,
            "subcategory": matched_subcategory,
            "workflow": localized_workflow,
            "localized_workflow": localized_workflow,
            "workflow_english": workflow_steps,
            "documents_required": documents_required,
            "required_documents": documents_required,
            "authorities": authorities,
            "complaint_template": complaint_template,
            "translation_triggered": translation_triggered,
            "cache_hit": cache_hit,
            "total": len(results),
            "message": message,
        }
    except Exception as exc:
        logger.exception("Guidance generation failed | request_id=%s error=%s", request_id, exc)
        return {
            "request_id": request_id,
            "query": query,
            "language": "en",
            "detected_language": "en",
            "normalized_query": query,
            "nlp": {
                "detected_language": "en",
                "understood_as": query,
                "keywords": [],
                "confidence": "Low",
                "nlp_source": "generator_error",
            },
            "ai_understanding": {},
            "data": [],
            "category_id": "",
            "category": "",
            "subcategory": "",
            "workflow": [],
            "localized_workflow": [],
            "workflow_english": [],
            "documents_required": [],
            "required_documents": [],
            "authorities": [],
            "complaint_template": "",
            "translation_triggered": False,
            "cache_hit": False,
            "total": 0,
            "message": "Search failed. Please try again.",
        }

