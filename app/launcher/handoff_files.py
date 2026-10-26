"""Engineering-only, non-atomic no-replace handoff primitives (Windows/NTFS).

No backup, journal or mutation authority lives here. The existing engine owns
those decisions. Both renames preserve collisions; the pathname can be absent.
"""

import ctypes
import msvcrt
import os
from contextlib import ExitStack, contextmanager
from ctypes import wintypes

from app.launcher.export_files import WindowsExportFiles
from app.launcher.write_files import WriteSafetyError, _kernel


class WindowsHandoffFiles(WindowsExportFiles):
    @contextmanager
    def pin(self, path):
        self.path(path.parent, directory=True)
        with ExitStack() as stack:
            for parent in reversed(path.parents):
                handle = self._directory_handle(parent)
                stack.callback(self._close_directory_handle, handle)
            yield

    @contextmanager
    def held(self, path, identity=None):
        path = self.path(path)
        kernel = _kernel()
        handle = kernel.CreateFileW(str(path), 0x80010000, 1, None, 3, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise WriteSafetyError("FILE_LOCKED_OR_ACCESS_DENIED")
        fd = None
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            handle = None
            with os.fdopen(fd, "rb", buffering=0) as stream:
                fd = None
                self.verify_name(stream, path)
                actual = self.identity(stream)
                if os.fstat(stream.fileno()).st_nlink != 1:
                    raise WriteSafetyError("REGULAR_SINGLE_LINK_FILE_REQUIRED")
                if identity is not None and list(identity) != actual:
                    raise WriteSafetyError("TARGET_IDENTITY_CHANGED")
                yield stream
        finally:
            if fd is not None:
                os.close(fd)
            if handle is not None:
                kernel.CloseHandle(handle)

    @staticmethod
    def identity(stream):
        value = os.fstat(stream.fileno())
        return [value.st_dev, value.st_ino]

    def verify_name(self, stream, path):
        actual = self._handle_path(msvcrt.get_osfhandle(stream.fileno()))
        if actual != os.path.normcase(str(path)):
            raise WriteSafetyError("OPENED_PATH_CHANGED")

    def delete_held(self, stream):
        """Delete exactly the held file (by handle, never by name) on close."""
        kernel = _kernel()
        kernel.SetFileInformationByHandle.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        )
        kernel.SetFileInformationByHandle.restype = wintypes.BOOL
        flag = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO.DeleteFile
        if not kernel.SetFileInformationByHandle(
            msvcrt.get_osfhandle(stream.fileno()), 4, ctypes.byref(flag), 1
        ):
            raise WriteSafetyError("RESIDUE_DELETE_FAILED")

    def rename_new(self, stream, destination):
        self.path(destination.parent, directory=True)

        class Info(ctypes.Structure):
            _fields_ = (
                ("Flags", wintypes.DWORD),
                ("Root", wintypes.HANDLE),
                ("Length", wintypes.DWORD),
                ("Name", wintypes.WCHAR * 1),
            )

        encoded = str(destination).encode("utf-16-le")
        payload = ctypes.create_string_buffer(ctypes.sizeof(Info) + len(encoded) + 2)
        info = Info.from_buffer(payload)
        info.Flags, info.Root, info.Length = 0, None, len(encoded)
        ctypes.memmove(
            ctypes.addressof(payload) + Info.Name.offset, encoded, len(encoded)
        )
        kernel = _kernel()
        kernel.SetFileInformationByHandle.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        )
        kernel.SetFileInformationByHandle.restype = wintypes.BOOL
        if not kernel.SetFileInformationByHandle(
            msvcrt.get_osfhandle(stream.fileno()), 3, payload, len(payload)
        ):
            error = ctypes.get_last_error()
            raise WriteSafetyError(
                "DESTINATION_OCCUPIED"
                if error in (80, 183)
                else "HANDOFF_RENAME_FAILED"
            )
        self.verify_name(stream, destination)
