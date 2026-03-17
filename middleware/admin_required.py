from __future__ import annotations

from fastapi import Depends, HTTPException, status

from middleware.auth_middleware import get_current_user


def admin_required(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
