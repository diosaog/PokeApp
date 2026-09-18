from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol


class RateLimitExceeded(RuntimeError):
    pass


class RateLimiter(Protocol):
    def check(self, *, key: str) -> None:
        ...


@dataclass
class InMemoryWindowRateLimiter:
    limit: int = 8
    window_seconds: int = 300
    _attempts: dict[str, deque[float]] = field(default_factory=dict)

    def check(self, *, key: str) -> None:
        now = time.monotonic()
        attempts = self._attempts.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= self.limit:
            raise RateLimitExceeded()
        attempts.append(now)


class NoopRateLimiter:
    def check(self, *, key: str) -> None:
        return None
