"""JWT auth decorators for user/admin route protection."""

from __future__ import annotations

from functools import wraps

from rest_framework.request import Request

from legal_cases.response_utils import error_response
from utils.logger import get_logger

from .auth_service import decode_jwt

logger = get_logger(__name__)


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ""
    return auth_header.split(" ", 1)[1].strip()


def require_user(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        token = _extract_token(request)
        if not token:
            return error_response("Missing auth token", status_code=401)
        try:
            payload = decode_jwt(token)
            request.auth_user = {
                "user_id": payload.get("user_id"),
                "role": payload.get("role", "user"),
            }
            return view_func(request, *args, **kwargs)
        except Exception:  # noqa: BLE001
            logger.warning("auth_failure path=%s", request.path)
            return error_response("Invalid or expired token", status_code=401)

    return _wrapped


def require_admin(view_func):
    @wraps(view_func)
    @require_user
    def _wrapped(request, *args, **kwargs):
        role = getattr(request, "auth_user", {}).get("role", "user")
        if role != "admin":
            return error_response("Admin access denied", status_code=403)
        return view_func(request, *args, **kwargs)

    return _wrapped
