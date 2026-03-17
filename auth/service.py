from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status

from auth.security import create_access_token, hash_password, verify_password
from models.auth_models import AuthResponse, LoginRequest, UserCreateRequest, UserPublic
from models.db import get_users_collection


def _to_user_public(document: dict) -> UserPublic:
    return UserPublic(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document.get("role", "user"),
        created_at=document["created_at"],
    )


def ensure_user_indexes() -> None:
    users = get_users_collection()
    users.create_index("email", unique=True)
    users.create_index("role")


def signup_user(payload: UserCreateRequest) -> AuthResponse:
    users = get_users_collection()
    existing = users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    document = {
        "name": payload.name.strip(),
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "role": "user",
        "created_at": datetime.now(UTC),
    }
    insert_result = users.insert_one(document)
    user_doc = users.find_one({"_id": insert_result.inserted_id})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")

    user = _to_user_public(user_doc)
    token = create_access_token(subject=user.id, role=user.role)
    return AuthResponse(access_token=token, user=user)


def login_user(payload: LoginRequest) -> AuthResponse:
    users = get_users_collection()
    user_doc = users.find_one({"email": payload.email.lower()})
    if not user_doc or not verify_password(payload.password, user_doc["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    role = user_doc.get("role", "user")
    if role != payload.login_as:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role mismatch for selected login")

    user = _to_user_public(user_doc)
    token = create_access_token(subject=user.id, role=user.role)
    return AuthResponse(access_token=token, user=user)


def get_user_by_id(user_id: str) -> dict | None:
    users = get_users_collection()
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return None
    return users.find_one({"_id": object_id})
