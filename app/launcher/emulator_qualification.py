"""Azahar qualification seam: identifying a candidate NEVER authorizes execution.

No lifecycle adapter is certified yet. Only tools may prepare an isolated copy;
the production runtime has no emulator launch/close or physical-write authority.
"""

import os
import stat
from hashlib import file_digest
from pathlib import Path

AZAHAR_VERSION = "2126.2"
AZAHAR_SHA256 = "c248414eb5328cb8bb720775ace6959898e2f50a0a10221c3a1e7a14190183eb"


def qualification_status():
    return {
        # Owner's primary emulator. No build is pinned or certified yet; running
        # lime3ds/azahar/citra processes already block every physical write.
        "primary_candidate": "Lime3DS",
        "primary_status": "PENDING_PINNED_BUILD_AND_REAL_GAME_QUALIFICATION",
        "candidate": "Azahar",
        "candidate_version": AZAHAR_VERSION,
        "status": "PENDING_REAL_GAME_QUALIFICATION",
        "qualified": False,
        "automatic_lifecycle_enabled": False,
        "requirements": [
            "isolated_legal_3ds_title",
            "in_game_save_flush_and_graceful_exit",
            "resource_release",
            "restart_exclusion_during_application_and_recovery",
            "in_game_applied_readback",
        ],
    }


def plain_local_path(path):
    path = Path(os.path.abspath(path))
    if os.name != "nt" or str(path).startswith("\\\\"):
        raise ValueError("LOCAL_WINDOWS_PATH_REQUIRED")
    for part in (path, *path.parents):
        info = part.lstat()
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("REPARSE_PATH_NOT_ALLOWED")
    return path


def inspect_azahar_candidate(executable):
    """Explicit read-only inspection. A recognized binary is still unqualified."""
    path = plain_local_path(executable)
    if path.name.lower() != "azahar.exe" or not path.is_file():
        raise ValueError("AZAHAR_EXECUTABLE_REQUIRED")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        digest = file_digest(stream, "sha256").hexdigest()
        after = os.fstat(stream.fileno())
    current = path.stat()

    def stamp(s):
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns

    if stamp(before) != stamp(after) or stamp(after) != stamp(current):
        raise ValueError("EXECUTABLE_CHANGED")
    if digest != AZAHAR_SHA256:
        raise ValueError("AZAHAR_VERSION_NOT_PINNED")
    return qualification_status() | {"sha256": digest, "path": str(path)}
