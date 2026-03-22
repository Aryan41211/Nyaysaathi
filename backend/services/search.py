"""Backend search orchestration service.

This module centralizes semantic search orchestration and singleton lifecycle,
while allowing app-level services (e.g., legal_cases/services.py) to remain stable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

_engine: Any | None = None


def get_engine():
    """Return singleton semantic engine instance."""
    global _engine
    if _engine is None:
        from search.semantic_engine import SemanticSearchEngine

        cache_dir = Path(getattr(settings, "SEARCH_CACHE_DIR", settings.BASE_DIR / "search_cache"))
        _engine = SemanticSearchEngine(cache_dir=cache_dir)
    return _engine


def semantic_search(cases: List[Dict], query: str, top_k: int = 5) -> Tuple[List[Dict], Dict]:
    """Execute semantic search over the loaded cases list."""
    engine = get_engine()
    engine.ensure_index(cases)
    return engine.semantic_search(query=query, top_k=top_k)


def reset_engine() -> None:
    """Reset singleton engine and in-memory state."""
    global _engine
    if _engine is not None:
        _engine.reset()
    _engine = None
    logger.info("Semantic engine reset")
