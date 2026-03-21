"""Standard API response helpers for NyaySaathi."""

from __future__ import annotations

from rest_framework.response import Response

DISCLAIMER = (
    "NyaySaathi provides procedural guidance only and does NOT constitute legal advice. "
    "For legal advice, please consult a qualified advocate. "
    "Free legal aid is available at your nearest District Legal Services Authority (DLSA) - call 15100."
)


def success_response(data, status_code: int = 200, **extra) -> Response:
    payload = {
        "success": True,
        "data": data,
        "error": None,
        "disclaimer": DISCLAIMER,
    }
    payload.update(extra)
    return Response(payload, status=status_code)


def error_response(error: str, message: str | None = None, status_code: int = 400, **extra) -> Response:
    payload = {
        "success": False,
        "data": None,
        "error": message or error,
        "status_code": status_code,
    }
    payload.update(extra)
    return Response(payload, status=status_code)
