"""Isolated fixture-only export prototype. Never imported by the Launcher.

Creates a new verified file, never replaces/renames/writes the source or an
existing destination. No business mutation, entitlement, sync, UI or receipt
consumption. The production registry and prior Phase22 engine remain unchanged.
"""

import ctypes
import os
import re
from contextlib import ExitStack, contextmanager
from ctypes import wintypes
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.launcher.write_engine import EngineeringCapability, PreparedNative, WriteIntent
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError, _kernel


@dataclass(frozen=True)
class ExportReceipt:
    operation_id: str
    source_sha256: str
    output_sha256: str
    output_path: str
    state: str = "EXPORTED_VERIFIED"
    applied_to_source: bool = False


def digest(data):
    return sha256(data).hexdigest()


def _path_from_handle(handle):
    kernel = _kernel()
    kernel.GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    count = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not 0 < count < len(buffer):
        raise WriteSafetyError("HANDLE_PATH_UNAVAILABLE")
    value = buffer.value
    value = value.removeprefix("\\\\?\\")
    return os.path.normcase(value)


@contextmanager
def _directory_handle(path):
    kernel = _kernel()
    # Existing object only; no delete sharing. Attributes are a separate threat.
    handle = kernel.CreateFileW(str(path), 0xA0, 3, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise WriteSafetyError("DIRECTORY_LOCK_UNAVAILABLE")
    try:
        if _path_from_handle(handle) != os.path.normcase(str(path)):
            raise WriteSafetyError("DIRECTORY_CHANGED")
        yield handle
    finally:
        kernel.CloseHandle(handle)


@contextmanager
def _stream(path, *, create=False):
    import msvcrt

    kernel = _kernel()
    # Source: READ only, SHARE_READ only. Export: new RW+DELETE handle, same share.
    access = 0xC0010000 if create else 0x80000000
    handle = kernel.CreateFileW(
        str(path), access, 1, None, 1 if create else 3, 0x00200000, None
    )
    if handle == ctypes.c_void_p(-1).value:
        raise WriteSafetyError("EXCLUSIVE_CREATE_OR_SOURCE_LOCK_FAILED")
    stream = None
    try:
        if _path_from_handle(handle) != os.path.normcase(str(path)):
            raise WriteSafetyError("OPENED_PATH_CHANGED")
        fd = msvcrt.open_osfhandle(
            handle, (os.O_RDWR if create else os.O_RDONLY) | os.O_BINARY
        )
        handle = None  # descriptor owns it now
        stream = os.fdopen(fd, "r+b" if create else "rb", buffering=0)
        if os.fstat(fd).st_nlink != 1:
            raise WriteSafetyError("MULTIPLE_LINKS_REJECTED")
        yield stream
    finally:
        if stream:
            stream.close()
        elif handle is not None:
            kernel.CloseHandle(handle)


def _publish_new(stream, directory_handle, basename):
    """Rename our still-locked new object relative to the directory handle.

    The Win32 wrapper rejects RootDirectory on the tested Windows build. Use the
    documented NtSetInformationFile FileRenameInformation user-mode operation,
    not an absolute-path fallback or any replacement operation.
    """
    import msvcrt

    class RenameInfo(ctypes.Structure):
        _fields_ = (
            ("Flags", wintypes.DWORD),  # union BOOLEAN ReplaceIfExists = FALSE
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        )

    encoded = basename.encode("utf-16-le")
    buffer = ctypes.create_string_buffer(ctypes.sizeof(RenameInfo) + len(encoded))
    info = RenameInfo.from_buffer(buffer)
    info.Flags = 0
    info.RootDirectory = directory_handle
    info.FileNameLength = len(encoded)
    ctypes.memmove(
        ctypes.addressof(buffer) + RenameInfo.FileName.offset, encoded, len(encoded)
    )

    class IoStatus(ctypes.Structure):
        _fields_ = (
            ("StatusOrPointer", ctypes.c_void_p),
            ("Information", ctypes.c_size_t),
        )

    native = ctypes.WinDLL("ntdll")
    native.NtSetInformationFile.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(IoStatus),
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.c_int,
    )
    native.NtSetInformationFile.restype = wintypes.LONG
    native.RtlNtStatusToDosError.argtypes = (wintypes.LONG,)
    native.RtlNtStatusToDosError.restype = wintypes.ULONG
    status = IoStatus()
    result = native.NtSetInformationFile(
        msvcrt.get_osfhandle(stream.fileno()),
        ctypes.byref(status),
        buffer,
        len(buffer),
        10,
    )
    if result != 0:
        # No fallback to replace, copy, unlink or open-existing.
        error = native.RtlNtStatusToDosError(result)
        raise WriteSafetyError(f"NO_REPLACE_PUBLICATION_FAILED_{error}")


class FixtureExportPrototype:
    def __init__(self, capability, native, *, hook=None):
        if type(capability) is not EngineeringCapability:
            raise WriteSafetyError("FIXTURE_CAPABILITY_REQUIRED")
        self.root = capability.fixture_root
        self.native = native
        self.files = WindowsWriteFiles()
        self.hook = hook or (lambda stage, paths: None)

    def export(self, source, destination_directory, intent):
        source = self.files.path(Path(source))
        directory = self.files.directory(Path(destination_directory))
        if (
            not source.is_relative_to(self.root)
            or not directory.is_relative_to(self.root)
            or directory == source.parent
            or intent.mutation.get("kind") != "test_marking"
        ):
            raise WriteSafetyError("ISOLATED_EXPORT_REQUIRED")
        intent = WriteIntent.create(**intent.to_payload())
        basename = f"export-{intent.operation_id}.save"
        assert re.fullmatch(r"export-[0-9a-f-]{36}\.save", basename)
        final = directory / basename
        stage = directory / f".export-{uuid4()}.partial"
        paths = {"source": source, "stage": stage, "final": final}
        # Pre-existing paths are NEVER opened for writing, including collision cases.
        with ExitStack() as stack:
            parents = sorted(
                set(source.parents) | {directory, *directory.parents},
                key=lambda p: len(p.parts),
            )
            handles = {p: stack.enter_context(_directory_handle(p)) for p in parents}
            self.files.path(source)
            self.files.path(directory, directory=True)
            source_stream = stack.enter_context(_stream(source))
            original = self.files.read(source_stream)
            if digest(original) != intent.expected_sha256:
                raise WriteSafetyError("SOURCE_HASH_CHANGED")
            self.hook("source_locked", paths)
            prepared = self.native.prepare(original, intent)
            if (
                not isinstance(prepared, PreparedNative)
                or prepared.game != intent.game
                or prepared.trainer_key != intent.trainer_key
                or prepared.source_hash != intent.expected_sha256
                or prepared.output_hash != digest(prepared.output)
                or len(prepared.output) != len(original)
                or prepared.output == original
            ):
                raise WriteSafetyError("INVALID_NATIVE_RESULT")
            self.native.verify(original, prepared.output, intent, prepared)
            output = stack.enter_context(_stream(stage, create=True))
            self.hook("stage_created", paths)
            if output.write(prepared.output) != len(prepared.output):
                raise WriteSafetyError("SHORT_WRITE")
            output.flush()
            os.fsync(output.fileno())
            self.native.verify(original, self.files.read(output), intent, prepared)
            if self.files.read(source_stream) != original:
                raise WriteSafetyError("SOURCE_CHANGED")
            self.hook("before_publish", paths)
            _publish_new(output, handles[directory], basename)
            self.hook("after_publish", paths)
            # Our handle remains non-write/non-delete-shared across publish/readback.
            os.fsync(output.fileno())
            self.native.verify(original, self.files.read(output), intent, prepared)
            if self.files.read(source_stream) != original:
                raise WriteSafetyError("SOURCE_CHANGED")
            import msvcrt

            if _path_from_handle(
                msvcrt.get_osfhandle(output.fileno())
            ) != os.path.normcase(str(final)):
                raise WriteSafetyError("PUBLISHED_PATH_CHANGED")
            self.hook("verified", paths)
            return ExportReceipt(
                intent.operation_id,
                intent.expected_sha256,
                prepared.output_hash,
                str(final),
            )

    def inspect(self, path, original, intent, prepared):
        """Read-only crash recovery using the exact retained source/plan.

        A caller without those materials cannot infer success. Does not retry,
        delete partial files, restore a backup, update current save or sync.
        """
        path = self.files.path(Path(path))
        if (
            not path.is_relative_to(self.root)
            or digest(original) != intent.expected_sha256
        ):
            raise WriteSafetyError("EXACT_RECOVERY_MATERIALS_REQUIRED")
        if path.name != f"export-{intent.operation_id}.save":
            raise WriteSafetyError("NOT_A_PUBLISHED_EXPORT_NAME")
        with _stream(path) as stream:
            data = self.files.read(stream)
            if digest(data) != prepared.output_hash:
                raise WriteSafetyError("EXPORT_CHANGED_OR_INCOMPLETE")
            self.native.verify(original, data, intent, prepared)
        return ExportReceipt(
            intent.operation_id, intent.expected_sha256, prepared.output_hash, str(path)
        )
