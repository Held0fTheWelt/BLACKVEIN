"""In-memory token bucket rate limiter."""

import time
from collections import defaultdict


class RateLimiter:
    """Token bucket rate limiter (30 calls/min default)."""

    def __init__(self, max_calls: int = 30, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str = "default") -> bool:
        """Check if client has quota remaining. Remove old tokens."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old tokens outside the window
        self.buckets[client_id] = [t for t in self.buckets[client_id] if t > cutoff]

        # Check if we can add a new token
        if len(self.buckets[client_id]) < self.max_calls:
            self.buckets[client_id].append(now)
            return True
        return False
