"""Small fixed-window limiters for a single backend instance."""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, max_keys: int = 10_000):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if key not in self._requests and len(self._requests) >= self.max_keys:
                oldest_key = min(self._requests, key=lambda item: self._requests[item][-1])
                del self._requests[oldest_key]
            requests = self._requests[key]
            while requests and now - requests[0] >= self.window_seconds:
                requests.popleft()
            if len(requests) >= self.max_requests:
                return False
            requests.append(now)
            return True


def enforce_limit(limiter: InMemoryRateLimiter, key: str) -> None:
    if not limiter.allow(key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")


chat_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60)
upload_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
list_limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)
delete_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
