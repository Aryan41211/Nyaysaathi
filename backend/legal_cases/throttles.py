"""Custom DRF throttles for NyaySaathi API endpoints."""

from __future__ import annotations

from rest_framework.throttling import ScopedRateThrottle


class ClassifyRateThrottle(ScopedRateThrottle):
    scope = "classify"
