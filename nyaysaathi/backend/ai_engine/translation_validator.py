"""Validation rules for translated legal workflow outputs."""
from __future__ import annotations

import re
from typing import Any

_MARKER_RE = re.compile(r"^\s*(\d+[\.)]|[\-\*])")


def _extract_marker(step: str) -> str:
    match = _MARKER_RE.match(step or "")
    return match.group(1) if match else ""


def validate_translation(original_steps: list[str], translated_steps: list[str]) -> bool:
    """
    Validate translated workflow integrity.

    Checks:
    - same number of steps
    - no empty translated steps
    - numbering/bullet markers preserved when present
    - sequence alignment preserved by index
    """
    if not original_steps or not translated_steps:
        return False

    if len(original_steps) != len(translated_steps):
        return False

    for original, translated in zip(original_steps, translated_steps):
        if not str(translated).strip():
            return False

        source_marker = _extract_marker(str(original))
        target_marker = _extract_marker(str(translated))
        if source_marker and source_marker != target_marker:
            return False

    return True


def enforce_valid_translation(original_steps: list[str], translated_steps: list[str]) -> list[str]:
    """Return validated translation, otherwise safe fallback to original workflow."""
    return translated_steps if validate_translation(original_steps, translated_steps) else list(original_steps)

