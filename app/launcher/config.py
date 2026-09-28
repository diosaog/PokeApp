from __future__ import annotations

import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from app.save_parser.files import SaveSource
from app.save_parser.models import WireModel


def backend_origin(value: str) -> str:
    url = urlsplit(value)
    if url.scheme != "https" and not (
        url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError("backend_requires_https")
    if (
        not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in ("", "/")
    ):
        raise ValueError("backend_origin_required")
    return value.rstrip("/")


def local_directory(path: Path, *, create=False) -> Path:
    raw = str(path)
    if raw.startswith(("\\\\", "//")) or (os.name == "nt" and ":" in raw[2:]):
        raise ValueError("local_directory_required")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    canonical = path.resolve(strict=True)
    if str(canonical).startswith(("\\\\", "//")) or not canonical.is_dir():
        raise ValueError("local_directory_required")
    return canonical


def state_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share")))
    return local_directory(base / "PokeApp" / "Launcher", create=True)


def atomic_write(path: Path, data: bytes) -> None:
    """For local config/metadata only; never used for replacing a live save."""
    handle, temporary = tempfile.mkstemp(prefix=".pokeapp-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class LauncherConfig(WireModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    selected_save: str | None = None
    folders: tuple[str, ...] = Field(default=(), max_length=20)
    backend_url: str | None = None
    auto_sync: bool = False
    poll_seconds: float = Field(default=5.0, ge=1, le=3600)
    debounce_seconds: float = Field(default=1.0, ge=0.25, le=60)

    @field_validator("backend_url")
    @classmethod
    def validate_backend(cls, value):
        return backend_origin(value) if value else None

    def source(self) -> SaveSource:
        if not self.selected_save:
            raise ValueError("select_save_required")
        return SaveSource.enroll(self.selected_save)

    @classmethod
    def load(cls, path: Path) -> LauncherConfig:
        if not path.exists():
            return cls()
        if path.stat().st_size > 65536:
            raise ValueError("invalid_launcher_config")
        return cls.model_validate_json(path.read_bytes())

    def save(self, path: Path) -> None:
        local_directory(path.parent, create=True)
        atomic_write(path, self.model_dump_json(indent=2).encode("utf-8"))
