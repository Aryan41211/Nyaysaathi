"""Compatibility facade for translation workflow."""

from .translator import get_translation_health, translate_workflow

__all__ = ["translate_workflow", "get_translation_health"]
