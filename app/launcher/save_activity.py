"""Local concurrency boundary: read/sync may overlap; physical writes never do."""

from contextlib import contextmanager
from functools import wraps
import threading


class SaveBusy(RuntimeError):
    pass


class SaveActivityGate:
    def __init__(self):
        self._lock = threading.RLock()
        self._readers = 0
        self._writer = False
        self.recovery_required = False

    @contextmanager
    def reading(self):
        with self._lock:
            if self._writer or self.recovery_required:
                raise SaveBusy("SAVE_WRITE_BUSY")
            self._readers += 1
        try:
            yield
        finally:
            with self._lock:
                self._readers -= 1

    @contextmanager
    def writing(self, *, recovery=False):
        with self._lock:
            if self._writer or self._readers or (self.recovery_required and not recovery):
                raise SaveBusy("SAVE_WRITE_BUSY")
            self._writer = True
        try:
            yield
        finally:
            with self._lock:
                self._writer = False


def save_read(function):
    """Keeps ordinary local reads available during slow cloud reads/uploads."""
    @wraps(function)
    def guarded(self, *args, **kwargs):
        with self.save_activity.reading():
            return function(self, *args, **kwargs)
    return guarded
