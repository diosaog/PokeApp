"""Certified Windows publication primitives for verified save exports.

An export creates a new name and never replaces the selected source or an
existing destination.  This module is intentionally Windows/NTFS-only and
fails closed everywhere else.
"""

from __future__ import annotations

import ctypes
import msvcrt
import os
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError, _kernel


class WindowsExportFiles(WindowsWriteFiles):
    """Low-level handles used only by the local export transaction."""

    @staticmethod
    def _handle_path(handle):
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
        return os.path.normcase(buffer.value.removeprefix("\\\\?\\"))

    def assert_export_supported(self):
        if os.name != "nt":
            raise WriteSafetyError("WINDOWS_NTFS_REQUIRED")
        # path() performs the actual NTFS and reparse checks; this also makes
        # unsupported drives fail before any journal or stage is created.
        self.path(Path.cwd(), directory=True)

    @contextmanager
    def strict_source(self, path: Path):
        self.assert_export_supported()
        path = self.path(path)
        kernel = _kernel()
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise WriteSafetyError("EXPORT_SOURCE_LOCK_FAILED")
        stream = None
        try:
            if self._handle_path(handle) != os.path.normcase(str(path)):
                raise WriteSafetyError("OPENED_PATH_CHANGED")
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            handle = None
            stream = os.fdopen(fd, "rb", buffering=0)
            if os.fstat(fd).st_nlink != 1:
                raise WriteSafetyError("MULTIPLE_LINKS_REJECTED")
            yield stream
        finally:
            if stream is not None:
                stream.close()
            elif handle is not None:
                kernel.CloseHandle(handle)

    @contextmanager
    def new_stage(self, path: Path):
        self.assert_export_supported()
        path = Path(path)
        self.path(path.parent, directory=True)
        kernel = _kernel()
        handle = kernel.CreateFileW(
            str(path),
            0xC0010000,
            1,
            None,
            1,
            0x00200000,
            None,
        )
        if handle == ctypes.c_void_p(-1).value:
            raise WriteSafetyError("EXPORT_DESTINATION_OCCUPIED")
        stream = None
        try:
            if self._handle_path(handle) != os.path.normcase(str(path)):
                raise WriteSafetyError("OPENED_PATH_CHANGED")
            fd = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
            handle = None
            stream = os.fdopen(fd, "r+b", buffering=0)
            yield stream
        finally:
            if stream is not None:
                stream.close()
            elif handle is not None:
                kernel.CloseHandle(handle)

    def publish_new(self, stream, final: Path):
        """Rename the held stage handle without replacing an existing name."""
        final = Path(final)
        self.path(final.parent, directory=True)
        if final.exists():
            raise WriteSafetyError("EXPORT_DESTINATION_OCCUPIED")

        class RenameInfo(ctypes.Structure):
            _fields_ = (
                ("Flags", wintypes.DWORD),
                ("RootDirectory", wintypes.HANDLE),
                ("FileNameLength", wintypes.DWORD),
                ("FileName", wintypes.WCHAR * 1),
            )

        encoded = final.name.encode("utf-16-le")
        payload = ctypes.create_string_buffer(ctypes.sizeof(RenameInfo) + len(encoded))
        info = RenameInfo.from_buffer(payload)
        info.Flags = 0
        directory_handle = self._directory_handle(final.parent)
        info.RootDirectory = directory_handle
        info.FileNameLength = len(encoded)
        ctypes.memmove(
            ctypes.addressof(payload) + RenameInfo.FileName.offset,
            encoded,
            len(encoded),
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
        try:
            result = native.NtSetInformationFile(
                msvcrt.get_osfhandle(stream.fileno()),
                ctypes.byref(status),
                payload,
                len(payload),
                10,
            )
        finally:
            self._close_directory_handle(directory_handle)
        if result != 0:
            error = native.RtlNtStatusToDosError(result)
            raise WriteSafetyError(f"EXPORT_PUBLICATION_FAILED_{error}")

    @staticmethod
    def _directory_handle(path):
        kernel = _kernel()
        handle = kernel.CreateFileW(str(path), 0xA0, 3, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise WriteSafetyError("EXPORT_DIRECTORY_LOCK_FAILED")
        return handle

    @staticmethod
    def _close_directory_handle(handle):
        if handle:
            _kernel().CloseHandle(handle)
