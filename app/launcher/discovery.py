from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Protocol

from app.launcher.config import local_directory
from app.save_parser.files import MAX_SAVE_BYTES, SaveSource, is_save_candidate
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
                if not is_save_candidate(path) or not entry.is_file(
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


# Citra-family emulators keep decrypted saves under sdmc/Nintendo 3DS/<id0>/<id1>/
# title/00040000/<title>/data/00000001/main. Lime3DS is the owner's primary.
EMULATOR_FOLDERS = ("Lime3DS", "Azahar", "Citra")
TITLE_GAMES = {
    "00055d00": "X",
    "00055e00": "Y",
    "0011c400": "OR",
    "0011c500": "AS",
    "00164800": "SN",
    "00175e00": "MN",
    "001b5000": "US",
    "001b5100": "UM",
}


@dataclass(frozen=True)
class EmulatorProvider:
    appdata: Path

    def candidates(self) -> tuple[SaveSource, ...]:
        found = []
        for emulator in EMULATOR_FOLDERS:
            base = self.appdata / emulator / "sdmc" / "Nintendo 3DS"
            if not base.is_dir():
                continue
            # Fixed depth, at most 4 console ids each level: no drive-wide scan.
            for id0 in sorted(p for p in base.iterdir() if len(p.name) == 32)[:4]:
                for id1 in sorted(p for p in id0.iterdir() if len(p.name) == 32)[:4]:
                    for title in TITLE_GAMES:
                        path = (
                            id1
                            / "title"
                            / "00040000"
                            / title
                            / "data"
                            / "00000001"
                            / "main"
                        )
                        if path.is_file() and not path.is_symlink():
                            source = SaveSource.enroll(path, "emulator")
                            if 0 < source.path.stat().st_size <= MAX_SAVE_BYTES:
                                found.append(source)
        return tuple(found)


def emulator_saves(appdata=None):
    """Display hints only: selection still enrolls the path and native parsing
    decides the real game. Never authorizes a write."""
    root = Path(appdata or os.environ.get("APPDATA", ""))
    if not root.is_dir():
        return []
    result = SaveDiscoveryService().discover((EmulatorProvider(root),))
    items = []
    for source in result.candidates:
        parts = source.path.parts
        emulator = next(
            (
                e
                for e in EMULATOR_FOLDERS
                if e.casefold() in (p.casefold() for p in parts)
            ),
            None,
        )
        title = parts[-4].casefold() if len(parts) >= 4 else ""
        items.append(
            {
                "path": str(source.path),
                "emulator": emulator,
                "game": TITLE_GAMES.get(title),
            }
        )
    return items
