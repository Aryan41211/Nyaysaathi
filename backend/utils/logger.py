"""Centralized logger factory for consistent structured backend logs."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return module logger with consistent naming usage."""
    return logging.getLogger(name)
