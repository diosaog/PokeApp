from __future__ import annotations

import os
from pathlib import Path

from app.launcher.backup import BackupService
from app.launcher.config import LauncherConfig, local_directory
from app.launcher.journal import LocalConflict, LocalJournal, LocalOperationQueue
from app.launcher.sync import SaveSyncService, SaveWatchService
from app.save_parser.adapter import SaveInspector


class LauncherLease:
    """OS-released single-instance lock for one local profile; no stale PID guessing."""

    def __init__(self, directory: Path):
        self.path = local_directory(directory, create=True) / "launcher.lock"
        self.stream = None

    def __enter__(self):
        if self.path.is_symlink():
            raise LocalConflict("INVALID_PROFILE_LOCK")
        self.stream = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.stream.write(b"0")
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            self.stream = None
            raise LocalConflict("LAUNCHER_ALREADY_RUNNING") from None
        return self

    def __exit__(self, *args):
        if self.stream:
            self.stream.close()  # releases lock on every supported OS, including process exit
            self.stream = None


class LauncherCore:
    def __init__(self, profile: Path, inspector: SaveInspector):
        self.profile = local_directory(profile, create=True)
        self.config_path = self.profile / "config.json"
        self.config = LauncherConfig.load(self.config_path)
        self.journal = LocalJournal(self.profile / "observations.sqlite3")
        self.queue = LocalOperationQueue(self.journal)
        self.sync = SaveSyncService(inspector, self.journal)
        self.backups = BackupService(self.profile / "backups", inspector)

    def select(self, path: Path):
        from app.save_parser.files import SaveSource

        selected = SaveSource.enroll(path)
        self.config = LauncherConfig.model_validate(
            self.config.model_dump() | {"selected_save": str(selected.path)}
        )
        self.config.save(self.config_path)

    def manual_sync(self):
        return self.sync.sync(self.config.source())

    def watcher(self):
        if not self.config.auto_sync:
            raise ValueError("auto_sync_disabled")
        return SaveWatchService(
            self.sync,
            self.config.source(),
            poll_seconds=self.config.poll_seconds,
            debounce_seconds=self.config.debounce_seconds,
        )

    def backup(self, requested_by="local-user"):
        source = self.config.source()
        snapshot = self.sync.inspector.reader.read(source)
        operation = self.queue.enqueue(
            kind="backup", requested_by=requested_by, expected=snapshot.fingerprint
        )
        self.queue.transition(operation, "PENDING", "RUNNING")
        try:
            ticket = self.backups.prepare(
                source, operation_id=operation, expected=snapshot.fingerprint
            )
            self.queue.transition(
                operation, "RUNNING", "SUCCESS", result={"backup_id": ticket.backup_id}
            )
            return ticket
        except Exception:
            self.queue.transition(operation, "RUNNING", "FAILED", error="BACKUP_FAILED")
            raise
