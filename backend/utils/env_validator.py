"""Environment validation helpers for startup safety."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class EnvValidationResult:
    missing_required: list[str]
    missing_optional: list[str]

    @property
    def is_valid(self) -> bool:
        return len(self.missing_required) == 0


def validate_environment() -> EnvValidationResult:
    debug = os.getenv("DEBUG", "True").lower() == "true"

    required = ["MONGODB_URI", "MONGODB_DB"]
    if not debug:
        required.extend(["DJANGO_SECRET_KEY", "ALLOWED_HOSTS", "JWT_SECRET"])

    optional = [
        "CORS_ALLOWED_ORIGINS",
        "CSRF_TRUSTED_ORIGINS",
        "OPENAI_API_KEY",
        "JWT_SECRET",
        "LOG_LEVEL",
    ]

    missing_required = [key for key in required if not os.getenv(key)]
    missing_optional = [key for key in optional if not os.getenv(key)]

    return EnvValidationResult(
        missing_required=missing_required,
        missing_optional=missing_optional,
    )
