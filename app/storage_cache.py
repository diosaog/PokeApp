from __future__ import annotations

import time
from typing import Any, Callable, Hashable


class ExpiringCache:
    def __init__(self, ttl_seconds: float) -> None:
        self.ttl_seconds = float(ttl_seconds)
        self._data: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: Hashable) -> tuple[bool, Any]:
        entry = self._data.get(key)
        if entry is None:
            return False, None
        ts, value = entry
        if (time.time() - float(ts)) <= self.ttl_seconds:
            return True, value
        self._data.pop(key, None)
        return False, None

    def set(self, key: Hashable, value: Any) -> None:
        self._data[key] = (time.time(), value)

    def clear(self, key: Hashable | None = None) -> None:
        if key is None:
            self._data.clear()
        else:
            self._data.pop(key, None)

    def clear_where(self, predicate: Callable[[Hashable], bool]) -> None:
        for key in list(self._data.keys()):
            if predicate(key):
                self._data.pop(key, None)
