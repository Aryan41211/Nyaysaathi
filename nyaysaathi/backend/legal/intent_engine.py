"""Intent engine: OpenAI call, JSON parsing, and response validation."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from openai import OpenAI

from .prompt_manager import ALLOWED_ACTION_TYPES, LEGAL_CATEGORIES, build_user_prompt, get_system_prompt


class AIUnderstandingError(RuntimeError):
    """Raised when AI understanding setup or model response is invalid."""


@dataclass(frozen=True)
class ModelConfig:
    """OpenAI model configuration for the understanding pipeline."""

    model: str = "gpt-4.1-mini"
    temperature: float = 0.2


class AIResponseValidator:
    """Validate and normalize LLM JSON output into canonical structure."""

    @staticmethod
    def _normalize_category(category: str) -> str:
        value = category.strip()
        if value in LEGAL_CATEGORIES:
            return value
        lowered = value.lower()
        for item in LEGAL_CATEGORIES:
            if item.lower() == lowered:
                return item
        return "Other"

    @staticmethod
    def _normalize_action_type(action_type: str) -> str:
        value = action_type.strip().lower().replace(" ", "_")
        return value if value in ALLOWED_ACTION_TYPES else "clarify_first"

    @staticmethod
    def _coerce_confidence(value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.25
        return max(0.0, min(1.0, score))

    @staticmethod
    def _coerce_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1"}:
                return True
            if lowered in {"false", "no", "0"}:
                return False
        return default

    @staticmethod
    def _coerce_str_list(value: Any, max_items: int = 4) -> list[str]:
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        elif isinstance(value, str) and value.strip():
            items = [part.strip() for part in value.split(",") if part.strip()]
        else:
            items = []
        return items[:max_items]

    @classmethod
    def normalize(cls, payload: dict[str, Any], user_input: str) -> dict[str, Any]:
        """Return schema-safe response object for downstream engines."""
        summary_default = "Unable to reliably determine the legal issue from the provided input."
        result: dict[str, Any] = {
            "intent": str(payload.get("intent", "unknown_legal_intent"))[:120].strip() or "unknown_legal_intent",
            "category": cls._normalize_category(str(payload.get("category", "Other"))),
            "subcategory": str(payload.get("subcategory", "General"))[:120].strip() or "General",
            "summary": str(payload.get("summary", summary_default))[:280].strip() or user_input[:280] or summary_default,
            "next_action_type": cls._normalize_action_type(str(payload.get("next_action_type", "clarify_first"))),
            "confidence": cls._coerce_confidence(payload.get("confidence", 0.25)),
            "is_legal": cls._coerce_bool(payload.get("is_legal"), True),
            "clarification_required": cls._coerce_bool(payload.get("clarification_required"), False),
            "clarification_questions": cls._coerce_str_list(payload.get("clarification_questions"), max_items=3),
            "additional_issues": cls._coerce_str_list(payload.get("additional_issues"), max_items=4),
        }
        return result


class IntentEngine:
    """Model-facing engine that gets semantic legal understanding from OpenAI."""

    def __init__(self, client: OpenAI, config: ModelConfig | None = None) -> None:
        self._client = client
        self._config = config or ModelConfig()

    @staticmethod
    def extract_json_object(raw_text: str) -> dict[str, Any]:
        """Safely parse a JSON object from model output."""
        text = (raw_text or "").strip()
        if not text:
            raise ValueError("Empty model response")

        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise ValueError("No JSON object found in model response")
            payload = json.loads(match.group(0))

        if not isinstance(payload, dict):
            raise ValueError("Model response JSON must be an object")
        return payload

    def understand(self, user_input: str, timeout: float) -> dict[str, Any]:
        """Call OpenAI and return normalized legal understanding payload."""
        response = self._client.chat.completions.create(
            model=self._config.model,
            temperature=self._config.temperature,
            response_format={"type": "json_object"},
            timeout=timeout,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": build_user_prompt(user_input)},
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        payload = self.extract_json_object(content)
        return AIResponseValidator.normalize(payload, user_input=user_input)


def get_openai_client() -> OpenAI:
    """Build OpenAI client from Django settings and environment."""
    api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        raise AIUnderstandingError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)
