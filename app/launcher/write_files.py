"""Windows-only physical-write primitives. No copy-over-target fallback.

ReplaceFileW is atomic on the supported local NTFS boundary, but is not a
compare-and-swap primitive. A delete-sharing handle is needed by ReplaceFileW.
Consequently same-user malicious renames cannot be excluded atomically; the
engine retains the displaced file as a witness and production actions stay off.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat
from typing import Callable


class WriteSafetyError(Exception):
    """A stable local code, never a pathname or native/parser diagnostic."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class EnrolledTarget:
    path: Path
    device: int
    inode: int


MAX_BYTES = 8 * 1024 * 1024
EMULATORS = (
    "citra",
    "lime3ds",
    "azahar",
    "mandarine",
    "mikage",
    "retroarch",
    "melonds",
    "desmume",
    "panda3ds",
    "lemonade",
)


def _kernel():
    if os.name != "nt":
        raise WriteSafetyError("WINDOWS_NTFS_REQUIRED")
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.ReplaceFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    )
    kernel.ReplaceFileW.restype = wintypes.BOOL
    kernel.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel.GetDriveTypeW.restype = wintypes.UINT
    kernel.GetVolumeInformationW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR,
        wintypes.DWORD,
    )
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    return kernel


def windows_process_names() -> tuple[str, ...]:
    """A native snapshot; a failed/incomplete enumeration never means no emulator."""
    import ctypes
    from ctypes import wintypes

    kernel = _kernel()

    class ProcessEntry(ctypes.Structure):
        _fields_ = (
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        )

    kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry))
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry))
    kernel.Process32NextW.restype = wintypes.BOOL
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise WriteSafetyError("PROCESS_CHECK_UNAVAILABLE")
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(handle, ctypes.byref(entry)):
            raise WriteSafetyError("PROCESS_CHECK_UNAVAILABLE")
        result = []
        while True:
            result.append(entry.szExeFile)
            if not kernel.Process32NextW(handle, ctypes.byref(entry)):
                if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                    raise WriteSafetyError("PROCESS_CHECK_UNAVAILABLE")
                break
        if not result:
            raise WriteSafetyError("PROCESS_CHECK_UNAVAILABLE")
        return tuple(result)
    finally:
        kernel.CloseHandle(handle)


class WindowsWriteFiles:
    def __init__(self, *, process_names: Callable = windows_process_names):
        self.process_names = process_names

    def assert_closed(self, confirmed: bool) -> None:
        if confirmed is not True:
            raise WriteSafetyError("CLOSE_EMULATOR_CONFIRMATION_REQUIRED")
        try:
            names = self.process_names()
            if any(
                any(prefix in name.casefold() for prefix in EMULATORS) for name in names
            ):
                raise WriteSafetyError("EMULATOR_RUNNING")
        except WriteSafetyError:
            raise
        except Exception:
            raise WriteSafetyError("PROCESS_CHECK_UNAVAILABLE") from None

    def path(self, path: Path, *, directory: bool = False) -> Path:
        import ctypes
        from ctypes import wintypes

        kernel = _kernel()
        path = Path(path)
        text = str(path)
        if (
            not path.is_absolute()
            or text.startswith(("\\\\", "//"))
            or ":" in text[2:]
            or "\0" in text
            or any(
                part in (".", "..") or part.endswith((" ", "."))
                for part in path.parts[1:]
            )
        ):
            raise WriteSafetyError("UNSAFE_PATH")
        # Inspect components before resolving: resolving first hides junctions.
        for component in reversed((path, *path.parents)):
            metadata = component.lstat()
            if (
                stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & 0x400
            ):
                raise WriteSafetyError("REPARSE_POINT_REJECTED")
        resolved = path.resolve(strict=True)
        if os.path.normcase(str(resolved)) != os.path.normcase(text):
            raise WriteSafetyError("PATH_CHANGED")
        metadata = resolved.stat()
        if directory:
            if not stat.S_ISDIR(metadata.st_mode):
                raise WriteSafetyError("DIRECTORY_REQUIRED")
        elif not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise WriteSafetyError("REGULAR_SINGLE_LINK_FILE_REQUIRED")
        root = resolved.anchor
        filesystem = ctypes.create_unicode_buffer(64)
        serial, max_component, flags = (
            wintypes.DWORD(),
            wintypes.DWORD(),
            wintypes.DWORD(),
        )
        if (
            kernel.GetDriveTypeW(root) != 3
            or not kernel.GetVolumeInformationW(
                root,
                None,
                0,
                ctypes.byref(serial),
                ctypes.byref(max_component),
                ctypes.byref(flags),
                filesystem,
                len(filesystem),
            )
            or filesystem.value != "NTFS"
        ):
            raise WriteSafetyError("LOCAL_NTFS_REQUIRED")
        return resolved

    def enroll(self, path: Path) -> EnrolledTarget:
        path = self.path(path)
        metadata = path.stat()
        if not 0 < metadata.st_size <= MAX_BYTES:
            raise WriteSafetyError("INVALID_SAVE_SIZE")
        if getattr(metadata, "st_file_attributes", 0) & 1:
            raise WriteSafetyError("TARGET_READ_ONLY")
        return EnrolledTarget(path, metadata.st_dev, metadata.st_ino)

    def directory(self, path: Path, *, create: bool = False) -> Path:
        path = Path(path).absolute()
        if create and not path.exists():
            self.path(path.parent, directory=True)
            path.mkdir()
        return self.path(path, directory=True)

    @contextmanager
    def locked(self, target: EnrolledTarget, *, check_identity: bool = True):
        """Deny writers and pin ancestor directories against rename/deletion.

        Read/delete sharing is necessary for ReplaceFileW. A process using a
        renamed handle or replacing the filename is addressed by witnesses and
        postchecks, not falsely described as an OS-level CAS guarantee.
        """
        import ctypes
        import msvcrt

        kernel = _kernel()
        path = self.path(target.path)
        directories, stream = [], None
        try:
            for directory in reversed(path.parents):
                handle = kernel.CreateFileW(
                    str(directory),
                    0x80,
                    3,
                    None,
                    3,
                    0x02000000 | 0x00200000,
                    None,
                )
                if handle == ctypes.c_void_p(-1).value:
                    raise WriteSafetyError("DIRECTORY_LOCK_UNAVAILABLE")
                directories.append(handle)
            # GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE; no write sharing.
            handle = kernel.CreateFileW(
                str(path),
                0x80000000,
                5,
                None,
                3,
                0x00200000,
                None,
            )
            if handle == ctypes.c_void_p(-1).value:
                raise WriteSafetyError("FILE_LOCKED_OR_ACCESS_DENIED")
            try:
                descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except BaseException:
                kernel.CloseHandle(handle)
                raise
            stream = os.fdopen(descriptor, "rb")
            metadata = os.fstat(stream.fileno())
            if (
                metadata.st_nlink != 1
                or not stat.S_ISREG(metadata.st_mode)
                or (
                    check_identity
                    and (metadata.st_dev, metadata.st_ino)
                    != (target.device, target.inode)
                )
            ):
                raise WriteSafetyError("TARGET_IDENTITY_CHANGED")
            self.assert_same_path(path, metadata.st_dev, metadata.st_ino)
            yield stream
        finally:
            if stream is not None:
                stream.close()
            for handle in reversed(directories):
                kernel.CloseHandle(handle)

    def assert_same_path(self, path: Path, device: int, inode: int):
        actual = self.path(path).stat()
        if (actual.st_dev, actual.st_ino) != (device, inode):
            raise WriteSafetyError("TARGET_IDENTITY_CHANGED")

    @staticmethod
    def read(stream) -> bytes:
        stream.seek(0)
        before = os.fstat(stream.fileno())
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
        if (
            not 0 < len(data) <= MAX_BYTES
            or before.st_size != len(data)
            or (before.st_size, before.st_mtime_ns)
            != (after.st_size, after.st_mtime_ns)
        ):
            raise WriteSafetyError("SAVE_CHANGED_DURING_READ")
        return data

    def read_path(self, path: Path) -> bytes:
        path = self.path(path)
        metadata = path.stat()
        target = EnrolledTarget(path, metadata.st_dev, metadata.st_ino)
        with self.locked(target) as stream:
            return self.read(stream)

    @contextmanager
    def operation_lock(self, path: Path):
        import ctypes

        kernel = _kernel()
        self.path(path.parent, directory=True)
        if path.exists():
            self.path(path)
        handle = kernel.CreateFileW(str(path), 0xC0000000, 0, None, 4, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise WriteSafetyError("WRITE_ALREADY_RUNNING")
        try:
            yield
        finally:
            kernel.CloseHandle(handle)

    def create_verified(self, path: Path, data: bytes, *, immutable: bool = False):
        self.path(path.parent, directory=True)
        # Exclusive creation; existing artifacts are never silently replaced.
        with path.open("xb") as stream:
            if stream.write(data) != len(data):
                raise WriteSafetyError("SHORT_WRITE")
            stream.flush()
            os.fsync(stream.fileno())
        if (
            len(data) != path.stat().st_size
            or sha256(self.read_path(path)).digest() != sha256(data).digest()
        ):
            raise WriteSafetyError("ARTIFACT_VERIFICATION_FAILED")
        if immutable:
            os.chmod(path, stat.S_IREAD)

    def replace(self, target: Path, stage: Path, witness: Path):
        if target.parent != stage.parent or target.parent != witness.parent:
            raise WriteSafetyError("SAME_DIRECTORY_REQUIRED")
        if witness.exists():
            raise WriteSafetyError("REPLACEMENT_WITNESS_EXISTS")
        self.path(stage)
        kernel = _kernel()
        # Flags=0: REPLACEFILE_WRITE_THROUGH is documented as unsupported.
        # Stage fsync precedes this call; destination fsync and readback follow.
        if not kernel.ReplaceFileW(
            str(target), str(stage), str(witness), 0, None, None
        ):
            raise WriteSafetyError("ATOMIC_REPLACE_FAILED")

    def flush(self, path: Path):
        self.path(path)
        with path.open("r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
