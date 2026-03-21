"""Input validation helpers for API request payloads."""

from __future__ import annotations

import re

MAX_INPUT_LENGTH = 500
MIN_INPUT_LENGTH = 3

_INJECTION_PATTERN = re.compile(
    r"(\b(select|insert|update|delete|drop|union|alter|truncate|exec|xp_)\b|--|/\*|\*/|;|<script|javascript:)",
    flags=re.IGNORECASE,
)


def validate_user_text(value: str, field_name: str = "input") -> tuple[bool, str]:
    text = str(value or "").strip()
    if not text:
        return False, f"{field_name} is required"
    if len(text) < MIN_INPUT_LENGTH:
        return False, f"{field_name} is too short"
    if len(text) > MAX_INPUT_LENGTH:
        return False, f"{field_name} is too long (max {MAX_INPUT_LENGTH} characters)"
    if _INJECTION_PATTERN.search(text):
        return False, f"{field_name} contains blocked characters or patterns"
    return True, ""
