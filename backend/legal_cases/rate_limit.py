"""Simple cache-backed per-user rate limiting for classify endpoint."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from django.core.cache import cache

_LIMIT_LOCK = Lock()
_WINDOW_SECONDS = 60
_MAX_REQUESTS = 20


def is_rate_limited(user_key: str) -> bool:
    key = f"classify:rl:{user_key}"
    now = time.time()

    with _LIMIT_LOCK:
        existing = cache.get(key)
        timestamps = deque(existing or [])
        while timestamps and now - timestamps[0] > _WINDOW_SECONDS:
            timestamps.popleft()

        if len(timestamps) >= _MAX_REQUESTS:
            cache.set(key, list(timestamps), timeout=_WINDOW_SECONDS)
            return True

        timestamps.append(now)
        cache.set(key, list(timestamps), timeout=_WINDOW_SECONDS)
        return False
