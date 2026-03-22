"""API request logging and fallback error middleware."""

from __future__ import annotations

import json
import time

from django.http import JsonResponse

from utils.logger import get_logger

logger = get_logger(__name__)


class ApiRequestLogMiddleware:
    """Log API request latency and status for observability."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)

        if request.path.startswith("/api/"):
            logger.info(
                "api_request method=%s path=%s status=%s duration_ms=%s",
                request.method,
                request.path,
                getattr(response, "status_code", "unknown"),
                elapsed_ms,
            )
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
