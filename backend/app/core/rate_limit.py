"""In-memory sliding window rate limiter for security-sensitive endpoints (T-903)."""

import threading
import time
from collections import defaultdict
from typing import ClassVar

from app.core.config import get_settings
from app.core.errors import RateLimitedError


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter."""

    _instances: ClassVar[dict[str, "SlidingWindowRateLimiter"]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()
    enabled_in_tests: bool = False

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.hits: dict[str, list[float]] = defaultdict(list)
        self.instance_lock = threading.Lock()

    @classmethod
    def get_limiter(cls, name: str, limit: int, window_seconds: int = 60) -> "SlidingWindowRateLimiter":
        """Get or create named rate limiter singleton."""
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = cls(limit=limit, window_seconds=window_seconds)
            return cls._instances[name]

    def check(self, key: str) -> None:
        """Check if key has exceeded limit in sliding window. Raises RateLimitedError if so."""
        import sys

        is_test = "pytest" in sys.modules or get_settings().APP_ENV == "test"
        if is_test and not self.enabled_in_tests:
            return

        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self.instance_lock:
            timestamps = self.hits[key]
            # Prune timestamps older than window
            valid_timestamps = [t for t in timestamps if t > cutoff]
            if len(valid_timestamps) >= self.limit:
                retry_after = int(self.window_seconds - (now - valid_timestamps[0])) + 1
                raise RateLimitedError(
                    message=f"Too many requests. Please try again in {retry_after} second(s).",
                    details=[{"retry_after": retry_after, "limit": self.limit, "window_seconds": self.window_seconds}],
                )
            valid_timestamps.append(now)
            self.hits[key] = valid_timestamps

    def reset(self) -> None:
        """Reset all rate limiter state (useful for tests)."""
        with self.instance_lock:
            self.hits.clear()


# Pre-configured rate limiters per docs/SECURITY.md
# Login: 15 attempts / minute per IP
login_rate_limiter = SlidingWindowRateLimiter.get_limiter("auth_login", limit=15, window_seconds=60)

# Solver Generation: 15 solver runs / minute per IP
solver_rate_limiter = SlidingWindowRateLimiter.get_limiter("solver_generate", limit=15, window_seconds=60)
