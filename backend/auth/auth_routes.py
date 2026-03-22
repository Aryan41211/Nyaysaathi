"""Auth API routes for signup and login."""

from __future__ import annotations

from rest_framework.decorators import api_view

from legal_cases.response_utils import error_response, success_response

from .auth_service import login_user, signup_user


@api_view(["POST"])
def signup(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = str(request.data.get("password", ""))
    role = str(request.data.get("role", "user")).strip().lower() or "user"

    result = signup_user(email=email, password=password, role=role)
    if not result.get("ok"):
        message = str(result.get("error", "Signup failed"))
        status_code = 503 if "temporarily unavailable" in message.lower() else 400
        return error_response(message, status_code=status_code)
    return success_response(result.get("data", {}), status_code=201)


@api_view(["POST"])
def login(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = str(request.data.get("password", ""))

    result = login_user(email=email, password=password)
    if not result.get("ok"):
        message = str(result.get("error", "Login failed"))
        status_code = 503 if "temporarily unavailable" in message.lower() else 401
        return error_response(message, status_code=status_code)
    return success_response(result.get("data", {}), status_code=200)
