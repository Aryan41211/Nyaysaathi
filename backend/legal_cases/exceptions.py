"""DRF exception handling for consistent API error envelopes."""

from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    message = str(detail or "Request failed")
    response.data = {
        "success": False,
        "data": None,
        "error": message,
        "status_code": response.status_code,
    }
    return response
