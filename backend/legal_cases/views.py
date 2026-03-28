"""
views.py – REST API for NyaySaathi
====================================

Search pipeline:
    raw query -> multilingual NLP understanding -> intent layer -> semantic retrieval -> safe workflow response

The NLP metadata is returned to the frontend so it can display:
  - detected language
  - what the system understood
  - confidence indicator
"""
import logging
import time

from django.http import JsonResponse
from rest_framework.decorators import api_view, throttle_classes

from auth.auth_middleware import require_admin, require_user
from . import services
from .async_queue import enqueue_search, get_search_task
from legal.admin_analytics import get_admin_queries, get_category_stats
from legal.query_logger import get_user_history, log_query, log_training_event, log_user_feedback
from services.workflow_service import localize_case_payload
from .observability import get_observability
from .rate_limit import is_rate_limited
from .response_utils import error_response, success_response
from .throttles import ClassifyRateThrottle, SearchRateThrottle
from .validators import validate_user_text

logger = logging.getLogger(__name__)


def _format_steps(steps: list[str]) -> list[str]:
    formatted: list[str] = []
    for idx, step in enumerate(steps or [], start=1):
        text = str(step or "").strip()
        if not text:
            continue
        if text.lower().startswith("step "):
            formatted.append(text)
        else:
            formatted.append(f"Step {idx}: {text}")
    return formatted


def _build_fallback_search_response(query: str):
    """Return local semantic/keyword fallback response payload."""
    results, nlp_meta = services.search_cases(query, top_k=5)
    normalized_results = []
    for row in results:
        workflow = row.get("workflow_steps") or row.get("workflow") or []
        normalized_results.append(
            {
                **row,
                "workflow": workflow,
                "workflow_steps": workflow,
            }
        )

    pipeline_response = services.build_standard_response(query=query, results=normalized_results, nlp_meta=nlp_meta)

    return success_response(
        normalized_results,
        query=query,
        language=nlp_meta.get("detected_language", "en"),
        detected_language=nlp_meta.get("detected_language", "en"),
        normalized_query=nlp_meta.get("normalized_query", query),
        nlp=nlp_meta,
        pipeline=pipeline_response,
        reasoning_signals=nlp_meta.get("reasoning_signals", {}),
        ai_understanding={},
        semantic_match={"source": "services.search_cases"},
        category="",
        subcategory="",
        workflow=[],
        workflow_steps=[],
        localized_workflow=[],
        workflow_english=[],
        documents_required=[],
        required_documents=[],
        authorities=[],
        complaint_template="",
        translation_triggered=False,
        cache_hit=False,
        clarification_required=nlp_meta.get("clarification_required", False),
        clarification_message=nlp_meta.get("clarification_message", ""),
        clarification_questions=nlp_meta.get("clarification_questions", []),
        total=len(normalized_results),
        message="Search completed using fallback semantic engine.",
    )


@api_view(["GET"])
def health(request):
    return JsonResponse({"status": "ok"})


@api_view(["GET"])
def categories_list(request):
    """GET /api/categories/"""
    try:
        cats = services.get_all_categories()
        return success_response(cats, total=len(cats))
    except Exception as e:
        logger.error("categories_list: %s", e)
        return error_response("categories_fetch_failed", "Could not fetch categories.", 500)


@api_view(["GET"])
def cases_list(request):
    """GET /api/cases/?category=xxx"""
    try:
        category = request.query_params.get("category")
        cases = services.get_all_cases(category=category)
        summary = [
            {
                "category":            c.get("category"),
                "subcategory":         c.get("subcategory"),
                "problem_description": (c.get("problem_description") or "")[:220],
            }
            for c in cases
        ]
        return success_response(summary, total=len(summary))
    except Exception as e:
        logger.error("cases_list: %s", e)
        return error_response("cases_fetch_failed", "Could not fetch cases.", 500)


@api_view(["GET", "POST"])
@throttle_classes([SearchRateThrottle])
def search(request):
    """
    GET /api/search/?query=<text>
    POST /api/search  {"query": "..."}

    Accepts any language / messy input.

    Response includes:
      data          – list of matched cases
      nlp           – what the NLP layer understood (language, normalized query, keywords, confidence)
      query         – original raw query
      total         – number of results
      message       – human readable status
    """
    if request.method == "POST":
        query = str(request.data.get("query", "")).strip()
        user_id = str(request.data.get("user_id", "anonymous")).strip() or "anonymous"
    else:
        query = request.query_params.get("query", "").strip()
        user_id = str(request.query_params.get("user_id", "anonymous")).strip() or "anonymous"
    started = time.perf_counter()
    ok_input, validation_error = validate_user_text(query, "query")
    if not ok_input:
        return error_response("invalid_query", validation_error, 400)

    # Fast outage path to keep p95 latency low when workflow DB is unavailable.
    try:
        from .db_connection import get_client

        if get_client(raise_on_error=False, quick=True) is None:
            logger.warning("Mongo quick probe failed in search; serving resilient fallback")
            return _build_fallback_search_response(query)
    except Exception as probe_exc:
        logger.warning("Search Mongo probe error, using fallback: %s", probe_exc)
        return _build_fallback_search_response(query)

    try:
        from ai_engine.response_generator import generate_legal_guidance

        guidance = generate_legal_guidance(query)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        pipeline_response = services.build_standard_response(
            query=query,
            results=list(guidance.get("data") or []),
            nlp_meta=dict(guidance.get("nlp") or {}),
        )
        nlp_meta = dict(guidance.get("nlp") or {})
        confidence = str(nlp_meta.get("confidence") or "Low")
        clarification_required = bool(guidance.get("clarification_required", False))
        get_observability().record_decision(
            query=query,
            normalized_query=str(guidance.get("normalized_query") or nlp_meta.get("search_ready_query") or query),
            intent=str(nlp_meta.get("matched_intent") or pipeline_response.get("intent") or "General legal issue"),
            confidence=confidence,
            decision="answer" if not clarification_required else "fallback",
            cache_hit=bool(guidance.get("cache_hit", False)),
            fallback=clarification_required,
            latency_ms=elapsed_ms,
        )
        try:
            log_training_event(
                user_id=user_id,
                query_raw=query,
                query_normalized=str(guidance.get("normalized_query") or nlp_meta.get("search_ready_query") or query),
                language=str(guidance.get("detected_language") or nlp_meta.get("detected_language") or "unknown"),
                intent=str(nlp_meta.get("matched_intent") or pipeline_response.get("intent") or "General legal issue"),
                confidence=confidence,
                decision="answer" if not clarification_required else "fallback",
                system_response=str(pipeline_response.get("answer") or ""),
                workflow_steps=list(guidance.get("workflow") or []),
                documents_required=list(guidance.get("documents_required") or []),
                request_id=str(guidance.get("request_id") or getattr(request, "request_id", "")),
                source=str((guidance.get("nlp") or {}).get("nlp_source") or "search"),
            )
        except Exception as log_exc:
            logger.warning("search training event log skipped: %s", log_exc)
        return success_response(
            guidance.get("data", []),
            request_id=guidance.get("request_id"),
            query=guidance.get("query", query),
            language=guidance.get("language", guidance.get("detected_language", "en")),
            category_id=guidance.get("category_id", ""),
            nlp=guidance.get("nlp", {}),
            pipeline=pipeline_response,
            reasoning_signals=guidance.get("reasoning_signals", {}),
            ai_understanding=guidance.get("ai_understanding", {}),
            semantic_match=guidance.get("semantic_match", {}),
            category=guidance.get("category", ""),
            subcategory=guidance.get("subcategory", ""),
            workflow=guidance.get("workflow", []),
            workflow_steps=guidance.get("workflow", []),
            localized_workflow=guidance.get("localized_workflow", []),
            workflow_english=guidance.get("workflow_english", []),
            documents_required=guidance.get("documents_required", []),
            required_documents=guidance.get("required_documents", []),
            authorities=guidance.get("authorities", []),
            complaint_template=guidance.get("complaint_template", ""),
            detected_language=guidance.get("detected_language", "en"),
            normalized_query=guidance.get("normalized_query", query),
            translation_triggered=guidance.get("translation_triggered", False),
            cache_hit=guidance.get("cache_hit", False),
            clarification_required=guidance.get("clarification_required", False),
            clarification_message=guidance.get("clarification_message", ""),
            clarification_questions=guidance.get("clarification_questions", []),
            debug={
                "request_id": getattr(request, "request_id", ""),
                "execution_time_ms": elapsed_ms,
            },
            total=guidance.get("total", 0),
            message=guidance.get("message", "Search completed."),
        )

    except Exception as e:
        logger.error("search '%s': %s", query, e)
        get_observability().record_error("search_view_exception")

        # Fallback to local semantic search so UI remains functional
        # even when upstream AI guidance dependencies are unavailable.
        try:
            return _build_fallback_search_response(query)
        except Exception as fallback_exc:
            logger.error("search fallback '%s': %s", query, fallback_exc)
            return error_response("search_failed", "Search failed. Please try again.", 500)


@api_view(["GET"])
def case_detail(request, subcategory):
    """GET /api/case/<subcategory>/"""
    try:
        requested_language = request.query_params.get("language", "en")
        normalised = subcategory.replace("-", " ").replace("%20", " ")
        case = services.get_case_by_subcategory(normalised)
        if not case:
            return error_response("case_not_found", f"No case found for: '{subcategory}'", 404)
        try:
            localized_case = localize_case_payload(case, requested_language)
        except Exception as localization_exc:
            logger.warning("case_detail localization fallback for '%s': %s", subcategory, localization_exc)
            localized_case = dict(case)
            docs = localized_case.get("required_documents") or localized_case.get("documents_required") or []
            localized_case["required_documents"] = list(docs)
            localized_case["documents_required"] = list(docs)
        return success_response(localized_case, language=requested_language)
    except Exception as e:
        logger.error("case_detail '%s': %s", subcategory, e)
        return error_response("case_detail_failed", "Could not fetch case details.", 500)


@api_view(["GET"])
def ai_health(request):
    """GET /api/health/ai/ - AI subsystem health for monitoring dashboards."""
    try:
        from ai_engine.translator import get_translation_health
        from legal.ai_engine import get_ai_monitoring_snapshot

        translation = get_translation_health()
        ai_snapshot = get_ai_monitoring_snapshot()
        runtime_observability = get_observability().snapshot()
        return success_response(
            {
                "ai_status": "ok",
                "translation_status": translation.get("translation_status", "unknown"),
                "cache_entries": translation.get("cache_entries", 0),
                "recent_errors": translation.get("recent_errors", []),
                "ai_monitor": ai_snapshot,
                "runtime_observability": runtime_observability,
            }
        )
    except Exception as exc:
        logger.error("ai_health failed: %s", exc)
        return success_response(
            {
                "ai_status": "degraded",
                "translation_status": "unknown",
                "cache_entries": 0,
                "recent_errors": [str(exc)],
                "runtime_observability": get_observability().snapshot(),
            }
        )


@api_view(["POST"])
@throttle_classes([ClassifyRateThrottle])
def classify(request):
    """POST /api/classify - classify user query and return workflow guidance payload."""
    user_input = str(request.data.get("user_input", "")).strip()
    user_id = str(request.data.get("user_id", "anonymous")).strip() or "anonymous"

    if is_rate_limited(user_id):
        return error_response("Rate limit exceeded. Try again in a minute.", status_code=429)

    ok_input, validation_error = validate_user_text(user_input, "user_input")
    if not ok_input:
        return error_response("invalid_user_input", validation_error, 400)

    try:
        started = time.perf_counter()
        output = services.classify_case(user_input)
        category = str(output.get("category", "Unknown"))
        confidence = str(output.get("confidence", "Low"))
        try:
            from .db_connection import get_client

            if get_client(raise_on_error=False, quick=True) is not None:
                log_query(user_id=user_id, query=user_input, category=category, confidence=confidence)
            else:
                logger.warning("Skipping classify query log because Mongo quick probe failed")
        except Exception as log_exc:
            logger.warning("Skipping classify query log due to DB error: %s", log_exc)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        clarification_required = bool(output.get("clarification_required", confidence.lower() == "low"))
        get_observability().record_decision(
            query=user_input,
            normalized_query=str(output.get("problem_summary") or user_input),
            intent=str(output.get("intent") or "guidance"),
            confidence=confidence,
            decision="answer" if not clarification_required else "fallback",
            cache_hit=False,
            fallback=clarification_required,
            latency_ms=elapsed_ms,
        )

        response_payload = {
            "problem_summary": output.get("problem_summary", output.get("matched_text", "")),
            "intent": output.get("intent", "guidance"),
            "category": category,
            "confidence": confidence,
            "similarity_score": output.get("similarity_score", 0.0),
            "matched_text": output.get("matched_text", ""),
            "workflow_steps": _format_steps(output.get("workflow_steps", ["Please describe problem more clearly"])),
            "explanation": output.get("explanation", ""),
            "clarification_questions": output.get("clarification_questions", []),
            "clarification_required": clarification_required,
            "request_id": output.get("request_id", ""),
            "source": output.get("source", "fallback"),
            "execution_time_ms": elapsed_ms,
            "pipeline": {
                "intent": output.get("intent", "guidance"),
                "confidence": confidence,
                "answer": (output.get("workflow_steps") or ["Please share more details"])[0],
                "clarification": {
                    "required": clarification_required,
                    "message": output.get("explanation", ""),
                    "questions": output.get("clarification_questions", []),
                },
                "debug": {
                    "query": user_input,
                    "matched_text": output.get("matched_text", ""),
                    "similarity_score": output.get("similarity_score", 0.0),
                    "source": output.get("source", "fallback"),
                },
            },
        }
        logger.info(
            "classification user_id=%s category=%s confidence=%s execution_ms=%s source=%s",
            user_id,
            category,
            confidence,
            elapsed_ms,
            response_payload.get("source", "unknown"),
        )
        try:
            log_training_event(
                user_id=user_id,
                query_raw=user_input,
                query_normalized=str(response_payload.get("problem_summary") or user_input),
                language="unknown",
                intent=str(response_payload.get("intent") or "guidance"),
                confidence=confidence,
                decision="answer" if not clarification_required else "fallback",
                system_response=str((response_payload.get("pipeline") or {}).get("answer") or ""),
                workflow_steps=list(response_payload.get("workflow_steps") or []),
                documents_required=[],
                request_id=str(response_payload.get("request_id") or getattr(request, "request_id", "")),
                source=str(response_payload.get("source") or "classify"),
            )
        except Exception as log_exc:
            logger.warning("classify training event log skipped: %s", log_exc)
        return success_response(response_payload)
    except Exception as exc:
        logger.error("classify failed: %s", exc)
        get_observability().record_error("classify_view_exception")
        return error_response("classification_failed", "Classification failed. Please try again.", 500)


@api_view(["GET"])
@require_admin
def observability_snapshot(request):
    """GET /api/observability - live performance and safety metrics with alerts."""
    del request
    return success_response(get_observability().snapshot())


@api_view(["POST"])
def feedback(request):
    """POST /api/feedback - stores user quality signal and optional correction payload."""
    positive_raw = request.data.get("positive")
    positive = bool(positive_raw) if positive_raw is not None else None

    user_id = str(request.data.get("user_id", "anonymous")).strip() or "anonymous"
    request_id = str(request.data.get("request_id", "")).strip()
    query = str(request.data.get("query", "")).strip()
    system_response = str(request.data.get("system_response", "")).strip()
    correction = str(request.data.get("correction", "")).strip()
    corrected_intent = str(request.data.get("corrected_intent", "")).strip()
    corrected_language = str(request.data.get("corrected_language", "")).strip().lower()

    metadata = {
        "confidence": request.data.get("confidence", ""),
        "source": request.data.get("source", "feedback_api"),
    }

    log_user_feedback(
        user_id=user_id,
        request_id=request_id,
        query_raw=query,
        system_response=system_response,
        correction_text=correction,
        corrected_intent=corrected_intent,
        corrected_language=corrected_language,
        is_helpful=positive,
        metadata=metadata,
    )

    if positive is not None:
        get_observability().record_feedback(positive=positive)

    return success_response(
        {
            "recorded": True,
            "positive": positive,
            "correction_recorded": bool(correction),
            "request_id": request_id,
        }
    )


@api_view(["POST"])
def search_async_submit(request):
    """POST /api/search/async - enqueue semantic search for async processing."""
    query = str(request.data.get("query", "")).strip()
    top_k = int(request.data.get("top_k", 5))
    ok_input, validation_error = validate_user_text(query, "query")
    if not ok_input:
        return error_response("invalid_query", validation_error, 400)

    task = enqueue_search(query=query, top_k=min(max(top_k, 1), 10))
    return success_response(task, status_code=202)


@api_view(["GET"])
def search_async_status(request, task_id: str):
    """GET /api/search/async/<task_id>/ - fetch async search execution status/result."""
    return success_response(get_search_task(task_id))


@api_view(["GET"])
@require_user
def user_history(request):
    """GET /api/user/history?user_id=<id> - return query history for a user."""
    user_id = str(getattr(request, "auth_user", {}).get("user_id", "anonymous")).strip() or "anonymous"
    try:
        limit = min(max(int(request.query_params.get("limit", "50")), 1), 200)
        history = get_user_history(user_id=user_id, limit=limit)
        return success_response(history, user_id=user_id, total=len(history), limit=limit)
    except Exception as exc:
        logger.error("user_history failed: %s", exc)
        return error_response("user_history_failed", "Could not fetch user history.", 500)


@api_view(["GET"])
@require_admin
def admin_query_stats(request):
    """GET /api/admin/query-stats - return category frequency stats."""
    try:
        stats = get_category_stats()
        return success_response(stats)
    except Exception as exc:
        logger.error("admin_query_stats failed: %s", exc)
        return error_response("admin_stats_failed", "Could not fetch query statistics.", 500)


@api_view(["GET"])
@require_admin
def admin_queries(request):
    """GET /api/admin/queries - return recent query logs."""
    try:
        limit = min(max(int(request.query_params.get("limit", "100")), 1), 500)
        offset = max(int(request.query_params.get("offset", "0")), 0)
        rows = get_admin_queries(limit=limit, offset=offset)
        return success_response(rows, total=len(rows), limit=limit, offset=offset)
    except Exception as exc:
        logger.error("admin_queries failed: %s", exc)
        return error_response("admin_queries_failed", "Could not fetch admin queries.", 500)
