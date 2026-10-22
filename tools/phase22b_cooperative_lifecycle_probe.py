"""Phase 22B cooperative-emulator lifecycle proof on one disposable save copy.

This is a tools-only feasibility probe. It never opens an owner save, never
publishes a Launcher build and never changes the production mutation registry.
The child process models a supported emulator that agrees to close before the
Launcher acquires its exclusive write handle.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from hashlib import sha256
from pathlib import Path

from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_NONE = 0
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
MOVEFILE_REPLACE_EXISTING = 0x1
INVALID_HANDLE = ctypes.c_void_p(-1).value


def _kernel():
    if os.name != "nt":
        raise RuntimeError("WINDOWS_REQUIRED")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel.CloseHandle.restype = ctypes.c_int
    kernel.MoveFileExW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    )
    kernel.MoveFileExW.restype = ctypes.c_int
    return kernel


def _open_exclusive(path: Path):
    kernel = _kernel()
    handle = kernel.CreateFileW(
        str(path),
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_NONE,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE:
        raise OSError(ctypes.get_last_error(), "CreateFileW")
    return kernel, handle


def _child(path: Path) -> int:
    kernel, handle = _open_exclusive(path)
    print("READY", flush=True)
    command = sys.stdin.readline().strip()
    kernel.CloseHandle(handle)
    if command != "CLOSE":
        print("UNEXPECTED_COMMAND", flush=True)
        return 2
    print("CLOSED", flush=True)
    return 0


def _probe_writer(path: Path) -> int:
    try:
        kernel, handle = _open_exclusive(path)
    except OSError as error:
        print(json.dumps({"blocked": True, "errno": error.errno}))
        return 0
    kernel.CloseHandle(handle)
    print(json.dumps({"blocked": False}))
    return 0


def _readline(process: subprocess.Popen, timeout: float = 10.0) -> str:
    # readline itself blocks; measuring time around it is not a timeout.
    lines = queue.Queue()
    thread = threading.Thread(
        target=lambda: lines.put(process.stdout.readline()), daemon=True
    )
    thread.start()
    try:
        line = lines.get(timeout=timeout)
    except queue.Empty:
        raise RuntimeError("COOPERATIVE_EMULATOR_TIMEOUT") from None
    if not line:
        raise RuntimeError("COOPERATIVE_EMULATOR_EOF")
    thread.join(timeout=1)
    return line.strip()


def _attempt_rename(path: Path, destination: Path) -> tuple[bool, int | None]:
    kernel = _kernel()
    destination.write_bytes(b"rename-attempt")
    result = kernel.MoveFileExW(str(path), str(destination), MOVEFILE_REPLACE_EXISTING)
    if result:
        return True, None
    return False, ctypes.get_last_error()


def run(source: Path, evidence: Path) -> dict:
    if os.name != "nt":
        raise RuntimeError("WINDOWS_REQUIRED")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phase22b-cooperative-") as folder:
        root = Path(folder)
        target = root / "main"
        rename_target = root / "rename-target"
        shutil.copyfile(source, target)
        expected_hash = sha256(target.read_bytes()).hexdigest()
        files = WindowsWriteFiles(process_names=list)
        enrolled = files.enroll(target)
        child = subprocess.Popen(
            [sys.executable, __file__, "--child", str(target)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            if _readline(child) != "READY":
                raise RuntimeError("EMULATOR_DID_NOT_OPEN_EXCLUSIVELY")
            try:
                with files.locked(enrolled):
                    raise AssertionError("LOCK_UNEXPECTEDLY_ACQUIRED")
            except WriteSafetyError as error:
                blocked_while_running = error.code
            renamed, rename_error = _attempt_rename(target, rename_target)
            if renamed:
                raise AssertionError("COOPERATIVE_RENAME_UNEXPECTEDLY_SUCCEEDED")
            child.stdin.write("CLOSE\n")
            child.stdin.flush()
            if _readline(child) != "CLOSED":
                raise RuntimeError("EMULATOR_CLOSE_ACK_MISSING")
            child.wait(timeout=10)
            with files.locked(enrolled) as stream:
                after_close_bytes = files.read(stream)
                writer = subprocess.run(
                    [sys.executable, __file__, "--probe", str(target)],
                    capture_output=True,
                    text=True,
                    check=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                blocked_during_launcher_lock = json.loads(writer.stdout)
                if not blocked_during_launcher_lock.get("blocked"):
                    raise AssertionError("COOPERATIVE_WRITER_NOT_BLOCKED")
            result = {
                "status": "PASS",
                "architecture": "COOPERATIVE_EMULATOR_LIFECYCLE",
                "source_copy": str(source),
                "disposable_copy": True,
                "emulator_opened_exclusively": True,
                "launcher_lock_before_close": blocked_while_running,
                "rename_while_emulator_open": {
                    "blocked": True,
                    "winerror": rename_error,
                },
                "cooperative_close_acknowledged": True,
                "launcher_lock_after_close": True,
                "writer_blocked_during_launcher_lock": blocked_during_launcher_lock,
                "bytes_preserved": sha256(after_close_bytes).hexdigest()
                == sha256(target.read_bytes()).hexdigest()
                == expected_hash,
                "automatic_publication": False,
                "owner_or_production_data": False,
                "scope": "supported cooperative emulator only; no hostile actor claim",
            }
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
            for stream in (child.stdin, child.stdout, child.stderr):
                stream.close()
        if not result["bytes_preserved"]:
            raise AssertionError("DISPOSABLE_BYTES_CHANGED")
        evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("source", type=Path)
    cli.add_argument("--evidence", type=Path)
    cli.add_argument("--child", action="store_true")
    cli.add_argument("--probe", action="store_true")
    args = cli.parse_args()
    if args.child:
        return _child(args.source)
    if args.probe:
        return _probe_writer(args.source)
    if args.evidence is None:
        cli.error("--evidence is required for the parent probe")
    result = run(args.source.resolve(strict=True), args.evidence.resolve())
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
