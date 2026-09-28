"""Bounded local snapshots. File content identity is not trainer/capture authority."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat

from app.save_parser.models import ErrorCode, SaveError, SaveFingerprint

MAX_SAVE_BYTES = 8 * 1024 * 1024
EXTENSIONS = {".sav", ".dsv", ".srm"}


def file_error(exc: OSError) -> SaveError:
    if getattr(exc, "winerror", None) in (32, 33):
        return SaveError(ErrorCode.FILE_LOCKED)
    if isinstance(exc, FileNotFoundError):
        return SaveError(ErrorCode.SAVE_NOT_FOUND)
    return SaveError(ErrorCode.ACCESS_DENIED)


def canonical_path(value: str | Path) -> Path:
    text = str(value)
    if not text or text.startswith(("\\\\", "//")) or "\x00" in text:
        raise SaveError(ErrorCode.INVALID_PATH)
    # Reject device/UNC/ADS before resolve; recheck after resolving symlinks/junctions.
    if os.name == "nt" and ":" in text[2:]:
        raise SaveError(ErrorCode.INVALID_PATH)
    try:
        path = Path(value).expanduser().resolve(strict=True)
    except OSError as exc:
        raise file_error(exc) from None
    if str(path).startswith(("\\\\", "//")) or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
        raise SaveError(ErrorCode.INVALID_PATH)
    return path


@dataclass(frozen=True)
class SaveSource:
    """Enrolled by local selection/discovery only. Never hydrated from backend JSON."""
    path: Path
    provider: str = "manual"

    @classmethod
    def enroll(cls, path: str | Path, provider: str = "manual") -> SaveSource:
        return cls(canonical_path(path), provider)

    def verified_path(self) -> Path:
        if canonical_path(self.path) != self.path:
            raise SaveError(ErrorCode.INVALID_PATH)
        return self.path


@dataclass(frozen=True)
class FileMetadata:
    size: int
    mtime_ns: int
    device: int
    inode: int

    @classmethod
    def of(cls, value):
        if not stat.S_ISREG(value.st_mode):
            raise SaveError(ErrorCode.INVALID_PATH)
        # Windows stat(path) / fstat(handle) disagree on ctime semantics. Content
        # hash + mtime + actual file identity are the portable consistency check.
        return cls(value.st_size, value.st_mtime_ns, value.st_dev, value.st_ino)


@dataclass(frozen=True)
class SaveSnapshot:
    source: SaveSource
    metadata: FileMetadata
    fingerprint: SaveFingerprint
    data: bytes


class SnapshotReader:
    def read(self, source: SaveSource) -> SaveSnapshot:
        try:
            path = source.verified_path()
            initial = FileMetadata.of(path.stat())
            if initial.size == 0:
                raise SaveError(ErrorCode.TRUNCATED_SAVE)
            if initial.size > MAX_SAVE_BYTES:
                raise SaveError(ErrorCode.UNSUPPORTED_VERSION)
            with path.open("rb") as stream:
                opened = FileMetadata.of(os.fstat(stream.fileno()))
                data = stream.read(MAX_SAVE_BYTES + 1)
                after = FileMetadata.of(os.fstat(stream.fileno()))
            final = FileMetadata.of(source.verified_path().stat())
            if not (initial == opened == after == final) or len(data) != initial.size:
                raise SaveError(ErrorCode.SAVE_CHANGED_DURING_READ)
            return SaveSnapshot(source, final, SaveFingerprint(sha256=sha256(data).hexdigest(), size=len(data)), data)
        except OSError as exc:
            raise file_error(exc) from None

    def verify(self, snapshot: SaveSnapshot) -> None:
        check = self.read(snapshot.source)
        if check.metadata != snapshot.metadata or check.fingerprint != snapshot.fingerprint:
            raise SaveError(ErrorCode.SAVE_CHANGED_DURING_READ)
