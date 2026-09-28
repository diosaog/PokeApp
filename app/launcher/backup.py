from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from app.launcher.config import atomic_write, local_directory
from app.launcher.journal import LocalConflict, now
from app.save_parser.adapter import SaveInspector
from app.save_parser.files import SaveSource
from app.save_parser.models import SaveFingerprint


class PhysicalWritesDisabled(Exception):
    pass


@dataclass(frozen=True)
class PreparedWrite:
    operation_id: str
    backup_id: str
    original: SaveFingerprint


class BackupService:
    def __init__(self, root: Path, inspector: SaveInspector):
        self.root, self.inspector = local_directory(root, create=True), inspector

    def _root(self):
        if local_directory(self.root) != self.root:
            raise ValueError("backup_directory_changed")

    def prepare(
        self, source: SaveSource, *, operation_id: str, expected: SaveFingerprint
    ) -> PreparedWrite:
        operation_id = str(UUID(operation_id))
        self._root()
        parsed = self.inspector.inspect(source)
        snapshot = parsed.snapshot
        if snapshot.fingerprint != expected:
            raise LocalConflict("SAVE_FINGERPRINT_CHANGED")
        backup_id = str(uuid4())
        file = self.root / (backup_id + ".sav")
        # Exclusive creation: no existing save/backup can be replaced.
        with file.open("xb") as stream:
            stream.write(snapshot.data)
            stream.flush()
            os.fsync(stream.fileno())
        metadata = dict(
            schema_version=1,
            backup_id=backup_id,
            operation_id=operation_id,
            created_at=now(),
            fingerprint=expected.model_dump(),
            source_path=str(source.path),
            parser_version=parsed.parser_version,
        )
        atomic_write(
            self.root / (backup_id + ".json"),
            json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
        )
        ticket = PreparedWrite(operation_id, backup_id, expected)
        self.verify(ticket)
        self.inspector.reader.verify(snapshot)
        return ticket

    def verify(self, ticket: PreparedWrite) -> None:
        self._root()
        identifier = str(UUID(ticket.backup_id))
        path = self.root / (identifier + ".sav")
        metadata_path = self.root / (identifier + ".json")
        if path.is_symlink() or metadata_path.is_symlink():
            raise LocalConflict("BACKUP_INVALID")
        if (
            path.stat().st_size != ticket.original.size
            or metadata_path.stat().st_size > 65536
        ):
            raise LocalConflict("BACKUP_INVALID")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("backup_id") != identifier
            or metadata.get("operation_id") != ticket.operation_id
            or metadata.get("fingerprint") != ticket.original.model_dump()
            or sha256(path.read_bytes()).hexdigest() != ticket.original.sha256
        ):
            raise LocalConflict("BACKUP_INVALID")

    def apply(self, ticket: PreparedWrite, source: SaveSource):
        """Future implementation must verify ticket/source, temp output and recovery.

        Fail closed now, even with a real backup. No physical mutation authority.
        """
        raise PhysicalWritesDisabled("PHYSICAL_WRITES_DISABLED")
