"""Windows current-user DPAPI; never fall back to plaintext token persistence."""

import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path

from app.launcher.config import atomic_write


def protect(data: bytes, *, decrypt=False) -> bytes:
    if os.name != "nt":
        raise ValueError("secure_storage_unavailable")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    output = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [
        ctypes.POINTER(Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(Blob),
    ]
    fn.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    # UI forbidden, current-user binding (never CRYPTPROTECT_LOCAL_MACHINE).
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ValueError("secure_storage_unavailable")
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


class TokenStore:
    def __init__(self, profile: Path):
        self.path = profile / "session.dpapi"

    def save(self, origin, session):
        if self.path.is_symlink():
            raise ValueError("invalid_token_store")
        if session._tokens is None or session._principal is None:
            return self.clear()
        payload = {
            "origin": origin,
            "tokens": session._tokens.model_dump(),
            "principal": session._principal.model_dump(),
        }
        atomic_write(self.path, protect(json.dumps(payload).encode()))

    def load(self, origin, session):
        from app.launcher.backend import BackendPrincipal, SessionTokens

        if not self.path.exists():
            return
        if self.path.is_symlink() or self.path.stat().st_size > 65536:
            raise ValueError("invalid_token_store")
        data = json.loads(protect(self.path.read_bytes(), decrypt=True))
        if data["origin"] != origin:
            return
        # Cached identity is labelled stale until /me verifies it again.
        session._tokens = SessionTokens.model_validate(data["tokens"])
        session._principal = BackendPrincipal.model_validate(data["principal"])

    def clear(self):
        if self.path.is_symlink():
            raise ValueError("invalid_token_store")
        self.path.unlink(missing_ok=True)
