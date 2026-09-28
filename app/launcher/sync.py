from __future__ import annotations

from dataclasses import dataclass
import logging
import sqlite3
import threading
from uuid import uuid4

from app.launcher.journal import LocalConflict, LocalJournal
from app.save_parser.adapter import SaveInspector
from app.save_parser.files import SaveSnapshot, SaveSource
from app.save_parser.models import ErrorCode, SaveError, compare_observations

log = logging.getLogger("pokeapp.launcher")


@dataclass(frozen=True)
class SyncResult:
    status: str
    sync_id: str
    receipt_id: str | None = None
    error: str | None = None
    changes: tuple = ()
    destination: str = "LOCAL_OBSERVATION_JOURNAL"


class SaveSyncService:
    def __init__(self, inspector: SaveInspector, journal: LocalJournal):
        self.inspector, self.journal = inspector, journal
        self._mutex = threading.Lock()

    def sync(
        self, source: SaveSource, *, snapshot: SaveSnapshot | None = None
    ) -> SyncResult:
        sync_id = str(uuid4())
        if not self._mutex.acquire(blocking=False):
            return SyncResult("CONFLICT", sync_id, error="SYNC_IN_PROGRESS")
        try:
            previous = self.journal.head(source)
            snapshot = snapshot or self.inspector.reader.read(source)
            if snapshot.source != source:
                raise SaveError(ErrorCode.INVALID_PATH)
            if (
                previous
                and previous.fingerprint == snapshot.fingerprint
                and previous.parser_version == self.inspector.parser.version
            ):
                self.inspector.reader.verify(snapshot)
                return self._result("NO_CHANGE", sync_id, previous)
            parsed = self.inspector.inspect(source, snapshot)
            receipt, created = self.journal.record(
                source,
                expected=previous.id if previous else None,
                fingerprint=snapshot.fingerprint,
                parser_version=parsed.parser_version,
                observation=parsed.observation,
            )
            changes = (
                compare_observations(
                    previous.observation if previous else None, parsed.observation
                )
                if created
                else ()
            )
            return self._result(
                "SYNCED" if created else "NO_CHANGE", sync_id, receipt, changes=changes
            )
        except SaveError as exc:
            status = (
                "UNSUPPORTED"
                if exc.code
                in (ErrorCode.UNSUPPORTED_GAME, ErrorCode.UNSUPPORTED_VERSION)
                else "CONFLICT"
                if exc.code == ErrorCode.SAVE_CHANGED_DURING_READ
                else "INVALID"
                if exc.code
                in (
                    ErrorCode.CORRUPT_SAVE,
                    ErrorCode.TRUNCATED_SAVE,
                    ErrorCode.AMBIGUOUS_IDENTITY,
                )
                else "ERROR"
            )
            return self._result(status, sync_id, error=exc.code.value)
        except LocalConflict:
            return self._result("CONFLICT", sync_id, error="LOCAL_HEAD_CHANGED")
        except (sqlite3.Error, OSError, ValueError):
            return self._result("ERROR", sync_id, error="LOCAL_STATE_UNAVAILABLE")
        finally:
            self._mutex.release()

    def _result(self, status, sync_id, receipt=None, *, error=None, changes=()):
        log.info(
            "sync id=%s status=%s parser=%s error=%s",
            sync_id,
            status,
            self.inspector.parser.version,
            error,
        )
        return SyncResult(
            status, sync_id, receipt.id if receipt else None, error, changes
        )


class SaveWatchService:
    """UI/OS watcher hints plus mandatory bounded polling; caller owns scheduling."""

    def __init__(
        self,
        sync: SaveSyncService,
        source: SaveSource,
        *,
        poll_seconds=5.0,
        debounce_seconds=1.0,
    ):
        if poll_seconds < 1 or debounce_seconds < 0.25:
            raise ValueError("invalid_watch_interval")
        self.sync_service, self.source = sync, source
        self.poll_seconds, self.debounce_seconds = poll_seconds, debounce_seconds
        self.next_poll = 0.0
        self.last_poll = -poll_seconds
        self.pending = None
        self.stable_since = 0.0

    def notify(self, now: float):
        self.next_poll = min(self.next_poll, max(now, self.last_poll + 1.0))

    def tick(self, now: float) -> SyncResult | None:
        if now < self.next_poll:
            return None
        self.last_poll = now
        self.next_poll = now + self.poll_seconds
        try:
            snapshot = self.sync_service.inspector.reader.read(self.source)
        except SaveError as exc:
            self.pending = None
            return SyncResult("ERROR", str(uuid4()), error=exc.code.value)
        stamp = (snapshot.metadata, snapshot.fingerprint)
        if stamp != self.pending:
            self.pending, self.stable_since = stamp, now
            self.next_poll = now + self.debounce_seconds
            return None
        if now - self.stable_since < self.debounce_seconds:
            return None
        return self.sync_service.sync(self.source, snapshot=snapshot)
