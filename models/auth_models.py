from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


Role = Literal["user", "admin"]


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    login_as: Role = "user"


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class WorkflowCreateRequest(BaseModel):
    payload: dict[str, Any]


class WorkflowUpdateRequest(BaseModel):
    workflow_id: str
    updates: dict[str, Any]


class WorkflowDeleteRequest(BaseModel):
    workflow_id: str
