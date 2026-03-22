"""AI-first legal problem classifier with deterministic fallback."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from services.workflow_service import get_category_id_options, resolve_category_id

from .semantic_search import find_best_category

logger = logging.getLogger(__name__)


def classify_legal_problem(
    text: str,
    original_text: str = "",
    allow_ai: bool = True,
    legacy_fallback: Callable[[str], str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Classify legal query into a workflow category_id.

    Order:
            1) Semantic matcher
            2) Existing legacy fallback callback
    """
    query = (text or "").strip()
    if not query:
        return "", {"source": "none", "used_ai": False}

    options = get_category_id_options()

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
