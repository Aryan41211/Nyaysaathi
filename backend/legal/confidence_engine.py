"""Confidence scoring and deterministic calibration for legal understanding output."""

from __future__ import annotations

from typing import Any


class ConfidenceEngine:
    """Apply policy-driven confidence calibration for stable production behavior."""

    @staticmethod
    def calibrate(result: dict[str, Any], user_input: str) -> float:
        """Calibrate model confidence using deterministic business rules."""
        try:
            score = float(result.get("confidence_score", result.get("confidence", 0.25)))
        except (TypeError, ValueError):
            score = 0.25

        score = max(0.0, min(1.0, score))
        text = (user_input or "").strip()

        if len(text) < 20:
            score -= 0.15
        if len(text) > 700:
            score -= 0.05

        if result.get("clarification_required"):
            score = min(score, 0.65)
        if not result.get("is_legal", True):
            score = min(score, 0.45)
        if result.get("additional_issues"):
            score = min(score, 0.78)

        # Clamp in product-defined operational range.
        return max(0.2, min(0.95, score))
