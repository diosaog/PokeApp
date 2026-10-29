from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import time
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
EMULATOR_FOLDERS = ("Lime3DS", "Azahar", "Citra", "Mandarine", "Lemonade", "Borked3DS")
# Executable and folder name fragments of the same family (portable installs).
EMULATOR_KEYS = (
    "lime3ds",
    "lime-qt",
    "azahar",
    "citra",
    "mandarine",
    "lemonade",
    "borked3ds",
)
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


def _emulator_name(text):
    folded = text.casefold()
    for name in EMULATOR_FOLDERS:
        if name.casefold() in folded:
            return name
    return "Lime3DS" if "lime" in folded else None


@dataclass(frozen=True)
class SdmcRoot:
    """One place where an emulator may keep its virtual SD card."""

    emulator: str
    location: str  # appdata | custom | portable
    sdmc: Path


def _custom_sdmc(user_dir):
    """The SD folder chosen in the emulator's own settings, read as text from
    qt-config.ini ([Data%20Storage] sdmc_directory=...)."""
    config = user_dir / "config" / "qt-config.ini"
    try:
        if not config.is_file() or config.stat().st_size > 1024 * 1024:
            return None
        lines = config.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        key, _, value = line.partition("=")
        if key.strip() == "sdmc_directory" and value.strip().strip('"'):
            return Path(value.strip().strip('"'))
    return None


def _process_dirs():
    """Folders of running Citra-family emulators: portable mode keeps a 'user'
    folder beside the executable. Names and image paths only."""
    if os.name != "nt":
        return []
    import ctypes
    from ctypes import wintypes

    from app.launcher.write_files import windows_process_entries

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    folders = []
    for pid, name in windows_process_entries():
        if not any(key in name.casefold() for key in EMULATOR_KEYS):
            continue
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            continue
        try:
            size = wintypes.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                folders.append(Path(buffer.value).parent)
        finally:
            kernel.CloseHandle(handle)
    return folders


def _portable_bases():
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    bases = [
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "Escritorio",
        home / "OneDrive" / "Documents",
        home / "OneDrive" / "Documentos",
        home / "scoop" / "persist",
        home / "scoop" / "apps",
    ]
    if os.environ.get("LOCALAPPDATA"):
        bases.append(Path(os.environ["LOCALAPPDATA"]) / "Programs")
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        if os.environ.get(variable):
            bases.append(Path(os.environ[variable]))
    return bases


def _portable_user_dirs(bases, limit=200):
    """Emulator folders up to two levels under a few usual places, never a
    drive-wide scan: <base>/<lime3ds…>/user or <base>/<any>/<azahar…>/user."""
    found = []
    for base in bases:
        try:
            if not base.is_dir():
                continue
            first_level = sorted(p for p in base.iterdir() if p.is_dir())[:limit]
        except OSError:
            continue
        for first in first_level:
            folders = [first]
            if not _emulator_name(first.name):
                try:
                    folders = [
                        p
                        for p in sorted(first.iterdir())[:limit]
                        if _emulator_name(p.name) and p.is_dir()
                    ]
                except OSError:
                    continue
            for folder in folders:
                for user in (folder / "user", folder / "current" / "user", folder):
                    try:
                        if (user / "sdmc").is_dir() or (
                            user / "config" / "qt-config.ini"
                        ).is_file():
                            found.append((_emulator_name(folder.name), user))
                            break
                    except OSError:
                        break
    return found


def sdmc_roots(appdata, *, process_dirs=None, portable_bases=None):
    """Every SD folder to check, deduplicated, each with how it was found."""
    roots, seen = [], set()

    def add(emulator, location, sdmc):
        try:
            key = os.path.normcase(str(Path(sdmc).resolve()))
        except OSError:
            return
        if key not in seen:
            seen.add(key)
            roots.append(SdmcRoot(emulator, location, Path(sdmc)))

    def add_user(emulator, location, user):
        add(emulator, location, user / "sdmc")
        custom = _custom_sdmc(user)
        if custom is not None:
            add(emulator, "custom", custom)

    if appdata is not None:
        for emulator in EMULATOR_FOLDERS:
            add_user(emulator, "appdata", Path(appdata) / emulator)
    for folder in process_dirs if process_dirs is not None else _process_dirs():
        add_user(_emulator_name(folder.name) or "Lime3DS", "portable", folder / "user")
    for emulator, user in _portable_user_dirs(
        portable_bases if portable_bases is not None else _portable_bases()
    ):
        add_user(emulator, "portable", user)
    return roots


def _saves_in(root):
    """(saves, other titles, error) in one SD folder, or None when it does not
    exist. Fixed depth, at most 4 console ids per level."""
    base = root.sdmc / "Nintendo 3DS"
    try:
        if not base.is_dir():
            return None, 0, None
    except OSError:
        return None, 0, None
    saves, others = [], 0
    try:
        for id0 in sorted(p for p in base.iterdir() if len(p.name) == 32)[:4]:
            for id1 in sorted(p for p in id0.iterdir() if len(p.name) == 32)[:4]:
                titles = id1 / "title" / "00040000"
                if not titles.is_dir():
                    continue
                for title in sorted(titles.iterdir())[:300]:
                    game = TITLE_GAMES.get(title.name.casefold())
                    if game is None:
                        others += title.is_dir()
                        continue
                    path = title / "data" / "00000001" / "main"
                    if path.is_file() and not path.is_symlink():
                        source = SaveSource.enroll(path, "emulator")
                        if 0 < source.path.stat().st_size <= MAX_SAVE_BYTES:
                            saves.append((source, game))
    except PermissionError:
        return saves, others, "ACCESS_DENIED"
    except (OSError, SaveError, ValueError):
        return saves, others, "UNREADABLE"
    return saves, others, None


def discover_emulator_saves(appdata=None, *, process_dirs=None, portable_bases=None):
    """Display hints only: selection still enrolls the path and native parsing
    decides the real game. Never authorizes a write. Returns the saves and a
    report of every place found, so «no saves» can always say why."""
    root = appdata or os.environ.get("APPDATA")
    root = Path(root) if root and Path(root).is_dir() else None
    items, checked, seen = [], [], set()
    for sdmc in sdmc_roots(
        root, process_dirs=process_dirs, portable_bases=portable_bases
    ):
        saves, others, error = _saves_in(sdmc)
        if saves is None:
            continue  # nothing of this emulator there
        for source, game in saves:
            key = os.path.normcase(str(source.path))
            if key in seen:
                continue
            seen.add(key)
            try:
                # stat() only: the selector shows when each save last changed.
                modified = int(source.path.stat().st_mtime)
            except OSError:
                modified = None
            items.append(
                {
                    "path": str(source.path),
                    "emulator": sdmc.emulator,
                    "location": sdmc.location,
                    "game": game,
                    "modified": modified,
                }
            )
        checked.append(
            {
                "emulator": sdmc.emulator,
                "location": sdmc.location,
                "saves": len(saves),
                "other_titles": others,
                "error": error,
            }
        )
    items.sort(key=lambda s: (-(s["modified"] or 0), s["path"].casefold()))
    return items, {"checked": checked, "found": len(items), "at": int(time.time())}


@dataclass(frozen=True)
class EmulatorProvider:
    """The AppData emulator folders as a discovery provider."""

    appdata: Path

    def candidates(self) -> tuple[SaveSource, ...]:
        found, _report = discover_emulator_saves(
            self.appdata, process_dirs=[], portable_bases=[]
        )
        return tuple(SaveSource.enroll(s["path"], "emulator") for s in found)


def emulator_saves(appdata=None):
    """The saves under one AppData folder only (see discover_emulator_saves)."""
    root = Path(appdata or os.environ.get("APPDATA", ""))
    if not root.is_dir():
        return []
    return discover_emulator_saves(root, process_dirs=[], portable_bases=[])[0]
