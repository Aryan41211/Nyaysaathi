"""JWT auth service with bcrypt password hashing."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from django.conf import settings

from legal_cases.db_connection import get_collection

USERS_COLLECTION = "users"
JWT_SECRET = getattr(settings, "JWT_SECRET", os.getenv("JWT_SECRET", "change-this-secret-in-env"))
JWT_ALGORITHM = getattr(settings, "JWT_ALGORITHM", os.getenv("JWT_ALGORITHM", "HS256"))
JWT_EXP_HOURS = int(getattr(settings, "JWT_EXP_HOURS", os.getenv("JWT_EXP_HOURS", "24")))
JWT_ISSUER = str(getattr(settings, "JWT_ISSUER", os.getenv("JWT_ISSUER", "nyaysaathi"))).strip() or "nyaysaathi"

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_WEAK_JWT_SECRETS = {
    "",
    "change-this-secret-in-env",
    "changeme",
    "secret",
    "default",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _validate_password_strength(password: str) -> tuple[bool, str]:
    value = str(password or "")
    if len(value) < 8:
        return False, "Password must be at least 8 characters"
    if len(value) > 128:
        return False, "Password is too long"
    if not any(ch.isalpha() for ch in value):
        return False, "Password must include letters"
    if not any(ch.isdigit() for ch in value):
        return False, "Password must include numbers"
    return True, ""


def _validate_email_format(email: str) -> bool:
    return bool(_EMAIL_PATTERN.fullmatch(str(email or "").strip()))


def _jwt_secret_is_weak() -> bool:
    value = str(JWT_SECRET or "")
    normalized = value.strip().lower()
    return len(value) < 32 or normalized in _WEAK_JWT_SECRETS


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_jwt(user_id: str, role: str) -> str:
    if _jwt_secret_is_weak():
        raise ValueError("JWT secret is not configured securely")

    exp = _now_utc() + timedelta(hours=JWT_EXP_HOURS)
    now_ts = int(_now_utc().timestamp())
    payload = {
        "user_id": str(user_id),
        "role": str(role),
        "iss": JWT_ISSUER,
        "iat": now_ts,
        "nbf": now_ts,
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "nbf", "iss"]},
    )


def signup_user(email: str, password: str, role: str = "user") -> dict[str, Any]:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        return {"ok": False, "error": "Email is required", "status_code": 400}
    if not _validate_email_format(normalized_email):
        return {"ok": False, "error": "Invalid email format", "status_code": 400}

    ok_password, error = _validate_password_strength(password)
    if not ok_password:
        return {"ok": False, "error": error, "status_code": 400}

    try:
        users = get_collection(USERS_COLLECTION)
        existing = users.find_one({"email": normalized_email}, {"_id": 1})
    except Exception:
        return {"ok": False, "error": "Auth service temporarily unavailable"}

    if existing:
        return {"ok": False, "error": "Email already registered", "status_code": 409}

    now = _now_utc()
    doc = {
        "email": normalized_email,
        "password_hash": hash_password(password),
        # Public signup endpoint never grants admin role.
        "role": "user",
        "created_at": now,
        "updated_at": now,
    }
    try:
        inserted = users.insert_one(doc)
    except Exception:
        return {"ok": False, "error": "Auth service temporarily unavailable"}

    try:
        token = create_jwt(str(inserted.inserted_id), doc["role"])
    except Exception:
        return {"ok": False, "error": "Auth service temporarily unavailable", "status_code": 503}

    return {
        "ok": True,
        "data": {
            "user_id": str(inserted.inserted_id),
            "email": normalized_email,
            "role": doc["role"],
            "token": token,
            "expires_in_hours": JWT_EXP_HOURS,
        },
    }


def login_user(email: str, password: str) -> dict[str, Any]:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email or not password:
        return {"ok": False, "error": "Email and password are required", "status_code": 400}
    if not _validate_email_format(normalized_email):
        return {"ok": False, "error": "Invalid email format", "status_code": 400}

    try:
        users = get_collection(USERS_COLLECTION)
        user = users.find_one({"email": normalized_email})
    except Exception:
        return {"ok": False, "error": "Auth service temporarily unavailable"}

    if not user:
        return {"ok": False, "error": "Invalid credentials"}

    if not verify_password(password, str(user.get("password_hash", ""))):
        return {"ok": False, "error": "Invalid credentials"}

    try:
        token = create_jwt(str(user.get("_id")), str(user.get("role", "user")))
    except Exception:
        return {"ok": False, "error": "Auth service temporarily unavailable", "status_code": 503}

    return {
        "ok": True,
        "data": {
            "user_id": str(user.get("_id")),
            "email": normalized_email,
            "role": str(user.get("role", "user")),
            "token": token,
            "expires_in_hours": JWT_EXP_HOURS,
        },
    }
