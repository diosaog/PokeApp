"""Private local SQLite, separate from V1 and V2. No authoritative capture order."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from app.launcher.config import local_directory
from app.save_parser.files import SaveSource
from app.save_parser.models import ObservedSave, SaveFingerprint


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalConflict(Exception):
    pass


@dataclass(frozen=True)
class LocalReceipt:
    id: str
    revision: int
    fingerprint: SaveFingerprint
    parser_version: str
    observation: ObservedSave


class LocalJournal:
    def __init__(self, path: Path):
        self.path = local_directory(path.parent, create=True) / path.name
        if self.path.is_symlink():
            raise ValueError("journal_symlink_denied")
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported_local_schema")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY, source TEXT NOT NULL, revision INTEGER NOT NULL,
                    sha256 TEXT NOT NULL, size INTEGER NOT NULL, parser_version TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(source, revision));
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, requested_by TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    payload TEXT NOT NULL, result TEXT, error TEXT);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def key(source: SaveSource) -> str:
        return os.path.normcase(str(source.path))

    @staticmethod
    def receipt(row) -> LocalReceipt | None:
        if row is None:
            return None
        return LocalReceipt(
            row["id"],
            row["revision"],
            SaveFingerprint(sha256=row["sha256"], size=row["size"]),
            row["parser_version"],
            ObservedSave.model_validate_json(row["payload"]),
        )

    def head(self, source: SaveSource) -> LocalReceipt | None:
        with self.connection() as db:
            return self.receipt(
                db.execute(
                    "SELECT * FROM observations WHERE source=? ORDER BY revision DESC LIMIT 1",
                    (self.key(source),),
                ).fetchone()
            )

    def record(
        self,
        source: SaveSource,
        *,
        expected: str | None,
        fingerprint: SaveFingerprint,
        parser_version: str,
        observation: ObservedSave,
    ) -> tuple[LocalReceipt, bool]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            head = self.receipt(
                db.execute(
                    "SELECT * FROM observations WHERE source=? ORDER BY revision DESC LIMIT 1",
                    (self.key(source),),
                ).fetchone()
            )
            if (
                head
                and head.fingerprint == fingerprint
                and head.parser_version == parser_version
            ):
                return head, False
            if (head.id if head else None) != expected:
                raise LocalConflict("LOCAL_HEAD_CHANGED")
            receipt = LocalReceipt(
                str(uuid4()),
                head.revision + 1 if head else 1,
                fingerprint,
                parser_version,
                observation,
            )
            db.execute(
                "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)",
                (
                    receipt.id,
                    self.key(source),
                    receipt.revision,
                    fingerprint.sha256,
                    fingerprint.size,
                    parser_version,
                    observation.model_dump_json(),
                    now(),
                ),
            )
            return receipt, True


class LocalOperationQueue:
    def __init__(self, journal: LocalJournal):
        self.journal = journal

    def enqueue(
        self,
        *,
        kind: str,
        requested_by: str,
        expected: SaveFingerprint,
        payload: dict | None = None,
        operation_id: str | None = None,
    ) -> str:
        if (
            kind not in ("backup", "future_write")
            or not requested_by
            or len(requested_by) > 128
        ):
            raise ValueError("invalid_operation")
        identifier = str(UUID(operation_id)) if operation_id else str(uuid4())
        body = json.dumps(
            payload or {}, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        if len(body) > 16384:
            raise ValueError("operation_payload_too_large")
        fingerprint = expected.model_dump_json()
        with self.journal.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM operations WHERE id=?", (identifier,)
            ).fetchone()
            if existing:
                if (
                    existing["kind"],
                    existing["requested_by"],
                    existing["fingerprint"],
                    existing["payload"],
                ) != (kind, requested_by, fingerprint, body):
                    raise LocalConflict("OPERATION_ID_REUSED")
                return identifier
            db.execute(
                "INSERT INTO operations VALUES (?,?, 'PENDING',?,?,?,?,NULL,NULL)",
                (identifier, kind, now(), requested_by, fingerprint, body),
            )
        return identifier

    def get(self, identifier: str) -> dict:
        with self.journal.connection() as db:
            row = db.execute(
                "SELECT * FROM operations WHERE id=?", (str(UUID(identifier)),)
            ).fetchone()
            if not row:
                raise ValueError("operation_not_found")
            return dict(row)

    def transition(
        self,
        identifier: str,
        expected: str,
        target: str,
        *,
        result: dict | None = None,
        error: str | None = None,
    ):
        allowed = {
            ("PENDING", "RUNNING"),
            ("PENDING", "CANCELLED"),
            ("RUNNING", "SUCCESS"),
            ("RUNNING", "FAILED"),
        }
        if (expected, target) not in allowed:
            raise ValueError("invalid_operation_transition")
        with self.journal.connection() as db:
            changed = db.execute(
                "UPDATE operations SET status=?,result=?,error=? WHERE id=? AND status=?",
                (
                    target,
                    json.dumps(result) if result else None,
                    error,
                    str(UUID(identifier)),
                    expected,
                ),
            ).rowcount
            if changed != 1:
                raise LocalConflict("OPERATION_STATE_CHANGED")

    def recover_interrupted(self) -> int:
        """Call only after obtaining the single-instance Launcher lease."""
        with self.journal.connection() as db:
            return db.execute(
                "UPDATE operations SET status='FAILED',error='RECOVERY_REQUIRED' WHERE status='RUNNING'"
            ).rowcount
