from __future__ import annotations

from fastapi import APIRouter

from auth.service import login_user, signup_user
from models.auth_models import AuthResponse, LoginRequest, UserCreateRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(payload: UserCreateRequest) -> AuthResponse:
    return signup_user(payload)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    return login_user(payload)
