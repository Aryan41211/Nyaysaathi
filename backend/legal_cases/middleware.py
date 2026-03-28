"""API request logging and fallback error middleware."""

from __future__ import annotations

import json
import time
from uuid import uuid4

from django.http import JsonResponse

from utils.logger import get_logger

logger = get_logger(__name__)


class ApiRequestLogMiddleware:
    """Log API request latency and status for observability."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.request_id = request_id
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)

        if request.path.startswith("/api/"):
            payload = {
                "event": "api_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status": getattr(response, "status_code", "unknown"),
                "duration_ms": elapsed_ms,
            }

            try:
                data = getattr(response, "data", None)
                if isinstance(data, dict):
                    payload_data = data.get("data") if isinstance(data.get("data"), dict) else data
                    nlp = data.get("nlp") or {}
                    pipeline = data.get("pipeline") or {}
                    if not pipeline and isinstance(payload_data.get("pipeline"), dict):
                        pipeline = payload_data.get("pipeline")
                    if not nlp and isinstance(payload_data.get("nlp"), dict):
                        nlp = payload_data.get("nlp")

                    payload["query"] = str(data.get("query") or payload_data.get("query") or "")
                    payload["normalized_query"] = str(
                        data.get("normalized_query")
                        or payload_data.get("normalized_query")
                        or nlp.get("search_ready_query")
                        or nlp.get("normalized_query")
                        or ""
                    )
                    payload["intent"] = str(
                        payload_data.get("intent")
                        or pipeline.get("intent")
                        or nlp.get("matched_intent")
                        or ""
                    )
                    payload["confidence"] = str(
                        data.get("confidence")
                        or payload_data.get("confidence")
                        or pipeline.get("confidence")
                        or nlp.get("confidence")
                        or ""
                    )
                    decision = "answer"
                    clarification = pipeline.get("clarification") or {}
                    if (
                        bool(data.get("clarification_required", False))
                        or bool(payload_data.get("clarification_required", False))
                        or bool(clarification.get("required", False))
                    ):
                        decision = "fallback"
                    payload["final_decision"] = decision
            except Exception:
                pass

            logger.info(json.dumps(payload, ensure_ascii=True))

        try:
            response["X-Request-ID"] = request_id
        except Exception:
            pass
        return response


class ApiExceptionMiddleware:
    """Catch uncaught API exceptions and return standard error payload."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exc:  # noqa: BLE001
            if not request.path.startswith("/api/"):
                raise

            logger.exception("Uncaught API exception on %s: %s", request.path, exc)
            return JsonResponse(
                {
                    "success": False,
                    "data": None,
                    "error": "Internal server error",
                    "status_code": 500,
                },
                status=500,
            )


class ApiInputValidationMiddleware:
    """Guardrail for malformed or overly large API request payloads."""

    MAX_BYTES = 16 * 1024

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            length = request.META.get("CONTENT_LENGTH")
            if length:
                try:
                    if int(length) > self.MAX_BYTES:
                        return JsonResponse(
                            {
                                "success": False,
                                "data": None,
                                "error": "Request payload too large",
                                "status_code": 413,
                            },
                            status=413,
                        )
                except ValueError:
                    return JsonResponse(
                        {
                            "success": False,
                            "data": None,
                            "error": "Malformed content length header",
                            "status_code": 400,
                        },
                        status=400,
                    )

            if request.method in {"POST", "PUT", "PATCH"} and request.body:
                try:
                    json.loads(request.body.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    return JsonResponse(
                        {
                            "success": False,
                            "data": None,
                            "error": "Invalid JSON payload",
                            "status_code": 400,
                        },
                        status=400,
                    )

        return self.get_response(request)
