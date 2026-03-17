"""AI-first legal problem classifier with deterministic fallback."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from services.workflow_service import get_category_id_options, resolve_category_id

from .openai_service import get_openai_client
from .semantic_search import find_best_category

logger = logging.getLogger(__name__)


def _classify_with_ai(query: str, options: list[str]) -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.0,
        response_format={"type": "json_object"},
        timeout=8,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the legal query into one category_id from the provided list. "
                    "Return strict JSON with key category_id only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": query,
                        "allowed_category_ids": options,
                    },
                    ensure_ascii=True,
                ),
            },
        ],
    )
    payload = json.loads((response.choices[0].message.content or "").strip())
    category_id = str(payload.get("category_id", "")).strip()
    if category_id in options:
        return category_id
    return ""


def classify_legal_problem(
    text: str,
    original_text: str = "",
    allow_ai: bool = True,
    legacy_fallback: Callable[[str], str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Classify legal query into a workflow category_id.

    Order:
      1) GPT constrained classification (optional)
      2) Semantic fallback
      3) Existing legacy fallback callback
    """
    query = (text or "").strip()
    if not query:
        return "", {"source": "none", "used_ai": False}

    options = get_category_id_options()

    if allow_ai and options:
        try:
            category_id = _classify_with_ai(query, options)
            if category_id:
                return category_id, {"source": "ai", "used_ai": True}
        except Exception as exc:
            logger.warning("AI classification failed, using fallback: %s", exc)

    semantic = find_best_category(query)
    semantic_label = str(semantic.get("category", "")).strip()
    if semantic_label:
        category_id = resolve_category_id(semantic_label, query, original_text)
        if category_id:
            return category_id, {
                "source": f"semantic_{semantic.get('source', 'fallback')}",
                "used_ai": False,
                "semantic": semantic,
            }

    if legacy_fallback:
        try:
            fallback_id = str(legacy_fallback(query)).strip()
            if fallback_id:
                return fallback_id, {"source": "legacy_fallback", "used_ai": False}
        except Exception as exc:
            logger.warning("Legacy fallback classification failed: %s", exc)

    return "", {"source": "none", "used_ai": False}
