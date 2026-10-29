"""Local concurrency boundary: read/sync may overlap; physical writes never do."""

from contextlib import contextmanager
from functools import wraps
import threading


class SaveBusy(RuntimeError):
    pass


class SaveActivityGate:
    def __init__(self):
        self._lock = threading.RLock()
        self._idle = threading.Condition(self._lock)
        self._readers = {}  # thread id -> nested read depth
        self._writer = False
        self._waiting = 0
        self.recovery_required = False

    @contextmanager
    def reading(self):
        thread = threading.get_ident()
        with self._lock:
            # A write that is waiting goes first: no new read or upload starts,
            # while one already running may finish its nested steps.
            if (
                self._writer
                or self.recovery_required
                or (self._waiting and thread not in self._readers)
            ):
                raise SaveBusy("SAVE_WRITE_BUSY")
            self._readers[thread] = self._readers.get(thread, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                self._readers[thread] -= 1
                if not self._readers[thread]:
                    del self._readers[thread]
                if not self._readers:
                    self._idle.notify_all()

    @contextmanager
    def writing(self, *, recovery=False, wait=0.0):
        """`wait` seconds for reads of OTHER threads to finish. The cloud step
        holds a read for its whole round (several seconds on a slow link), so
        «Añadir a la bolsa» refused at that moment until 0.26.5. A read held by
        this same thread can never finish meanwhile and refuses at once."""
        with self._lock:
            if (
                self._writer
                or (self.recovery_required and not recovery)
                or threading.get_ident() in self._readers
            ):
                raise SaveBusy("SAVE_WRITE_BUSY")
            if self._readers:
                if wait <= 0:
                    raise SaveBusy("SAVE_WRITE_BUSY")
                self._waiting += 1
                try:
                    free = self._idle.wait_for(
                        lambda: not self._readers and not self._writer, wait
                    )
                finally:
                    self._waiting -= 1
                if not free or (self.recovery_required and not recovery):
                    raise SaveBusy("SAVE_WRITE_BUSY")
            self._writer = True
        try:
            yield
        finally:
            with self._lock:
                self._writer = False
                self._idle.notify_all()


def save_read(function):
    """Keeps ordinary local reads available during slow cloud reads/uploads."""
    @wraps(function)
    def guarded(self, *args, **kwargs):
        with self.save_activity.reading():
            return function(self, *args, **kwargs)
    return guarded
