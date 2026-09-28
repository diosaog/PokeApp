from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Protocol

from app.launcher.config import local_directory
from app.save_parser.files import EXTENSIONS, MAX_SAVE_BYTES, SaveSource
from app.save_parser.models import SaveError


class DiscoveryProvider(Protocol):
    def candidates(self) -> tuple[SaveSource, ...]: ...


@dataclass(frozen=True)
class ManualProvider:
    path: Path

    def candidates(self) -> tuple[SaveSource, ...]:
        return (SaveSource.enroll(self.path),)


@dataclass(frozen=True)
class FolderProvider:
    folder: Path

    def candidates(self) -> tuple[SaveSource, ...]:
        root = local_directory(self.folder)
        candidates = []
        # One user-selected folder, bounded enumeration, no recursive drive scan.
        with os.scandir(root) as entries:
            for index, entry in enumerate(entries):
                if index >= 10000:
                    raise ValueError("discovery_folder_too_large")
                path = Path(entry.path)
                if path.suffix.lower() not in EXTENSIONS or not entry.is_file(
                    follow_symlinks=False
                ):
                    continue
                source = SaveSource.enroll(path, "folder")
                if source.path.parent != root:
                    continue
                if 0 < source.path.stat().st_size <= MAX_SAVE_BYTES:
                    candidates.append(source)
        return tuple(sorted(candidates, key=lambda s: str(s.path).casefold()))


@dataclass(frozen=True)
class DiscoveryResult:
    candidates: tuple[SaveSource, ...]
    errors: tuple[str, ...]


class SaveDiscoveryService:
    def discover(self, providers: tuple[DiscoveryProvider, ...]) -> DiscoveryResult:
        found, errors = {}, []
        for provider in providers:
            try:
                for source in provider.candidates():
                    found[os.path.normcase(str(source.path))] = source
            except SaveError as exc:
                errors.append(exc.code.value)
            except (OSError, ValueError):
                errors.append("DISCOVERY_FAILED")
        return DiscoveryResult(
            tuple(found[key] for key in sorted(found)), tuple(errors)
        )
