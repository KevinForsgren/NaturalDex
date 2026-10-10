#!/usr/bin/env python3
"""
Minimal in-memory rate limiter.

Provides coarse per-key window limiting for discovery creation, model calls and
pairing challenges. It is intentionally simple and process-local; if a future
deployment needs to scale across workers it should be replaced with a shared
store (Redis). Not restart-heavy correctness is required of rate limiting.
"""

import threading
import time


class RateLimitedError(Exception):
    """Raised when a client exceeds a configured rate limit."""

    def __init__(self, retry_after: int = 0):
        super().__init__("Too many requests. Please slow down and try again.")
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self):
        self._bucket = {}     # key -> list of timestamps
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        """Allow up to ``limit`` calls per ``window_seconds`` for ``key``.

        Raises RateLimitedError when the limit is exceeded.
        """
        now = time.monotonic()
        with self._lock:
            stamp = now - window_seconds
            bucket = [t for t in self._bucket.get(key, []) if t > stamp]
            if len(bucket) >= limit:
                oldest = bucket[0]
                retry_after = int(window_seconds - (now - oldest)) + 1
                raise RateLimitedError(retry_after)
            bucket.append(now)
            self._bucket[key] = bucket


# Shared instance used across request handlers.
limiter = RateLimiter()