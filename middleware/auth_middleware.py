from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from auth.security import decode_access_token
from auth.service import get_user_by_id


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return auth_header[7:].strip()


def get_current_user(request: Request) -> dict:
    token = _extract_bearer_token(request)
    payload = decode_access_token(token)
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_current_user(request: Request) -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:].strip()
    payload = decode_access_token(token)
    return get_user_by_id(payload["sub"])
