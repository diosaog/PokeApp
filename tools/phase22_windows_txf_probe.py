"""Bounded TxF feasibility experiment on fresh dummy files, never save files.

This is research tooling, not a production write path. Microsoft discourages
new TxF dependencies; a successful local experiment is not release certification.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import subprocess
import sys
import uuid
from ctypes import wintypes as w
from datetime import UTC, datetime
from pathlib import Path

from phase22_windows_sharing_probe import (
    CANDIDATE,
    EXTERNAL,
    INVALID,
    ORIGINAL,
    READ,
    WRITE,
    kernel,
    opened,
    outcome,
    read_handle,
    run_child,
    validate_child_paths,
)


def libraries():
    k = kernel()
    t = ctypes.WinDLL("KtmW32", use_last_error=True)
    t.CreateTransaction.argtypes = [
        w.LPVOID,
        w.LPVOID,
        w.DWORD,
        w.DWORD,
        w.DWORD,
        w.DWORD,
        w.LPWSTR,
    ]
    t.CreateTransaction.restype = w.HANDLE
    for name in ("CommitTransaction", "RollbackTransaction"):
        getattr(t, name).argtypes = [w.HANDLE]
        getattr(t, name).restype = w.BOOL
    k.CreateFileTransactedW.argtypes = [
        w.LPCWSTR,
        w.DWORD,
        w.DWORD,
        w.LPVOID,
        w.DWORD,
        w.DWORD,
        w.HANDLE,
        w.HANDLE,
        w.LPVOID,
        w.LPVOID,
    ]
    k.CreateFileTransactedW.restype = w.HANDLE
    k.MoveFileTransactedW.argtypes = [
        w.LPCWSTR,
        w.LPCWSTR,
        w.LPVOID,
        w.LPVOID,
        w.DWORD,
        w.HANDLE,
    ]
    k.MoveFileTransactedW.restype = w.BOOL
    return k, t


def checked(result, step):
    if not result:
        raise OSError(ctypes.get_last_error(), step)
    return result


def prepare_and_wait(target):
    k, t = libraries()
    tx = t.CreateTransaction(None, None, 0, 0, 0, 0, "PokeApp isolated dummy probe")
    checked(tx != INVALID, "CreateTransaction")
    handles = []
    try:
        # Request transacted modification rights before checking existing bytes.
        h = k.CreateFileTransactedW(
            str(target), READ | WRITE, 7, None, 3, 0x80, None, tx, None, None
        )
        checked(h != INVALID, "CreateFileTransactedW target")
        handles.append(h)
        assert read_handle(h) == ORIGINAL
        k.CloseHandle(handles.pop())
        stage = target.with_name("transaction.stage")
        h = k.CreateFileTransactedW(
            str(stage), READ | WRITE, 7, None, 1, 0x80, None, tx, None, None
        )
        checked(h != INVALID, "CreateFileTransactedW stage")
        handles.append(h)
        count = w.DWORD()
        checked(
            k.WriteFile(h, CANDIDATE, len(CANDIDATE), ctypes.byref(count), None),
            "WriteFile stage",
        )
        assert count.value == len(CANDIDATE)
        k.CloseHandle(handles.pop())
        checked(
            k.MoveFileTransactedW(str(stage), str(target), None, None, 1, tx),
            "MoveFileTransactedW",
        )
        print(json.dumps({"ready": True, "pid": os.getpid()}), flush=True)
        command = sys.stdin.readline().strip()
        if command == "commit":
            result = outcome(t.CommitTransaction(tx))
        elif command == "rollback":
            result = outcome(t.RollbackTransaction(tx))
        else:
            raise ValueError("Unknown command")
        checked(result["success"], command)
        return {**result, "operation": command, "pid": os.getpid()}
    finally:
        for h in handles:
            k.CloseHandle(h)
        k.CloseHandle(tx)


def run_case(root, mode):
    folder = root / mode
    folder.mkdir()
    target, external = folder / "original.bin", folder / "external.bin"
    target.write_bytes(ORIGINAL)
    external.write_bytes(EXTERNAL)
    process = subprocess.Popen(
        [sys.executable, __file__, "--child", str(target)],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        ready = json.loads(process.stdout.readline())
        if not ready.get("ready"):
            process.communicate(timeout=10)
            return {"mode": mode, "status": "UNAVAILABLE", **ready}
        assert ready["pid"] != os.getpid()
        outside_handle, outside_error = opened(target, READ, 7)
        if outside_error:
            outside_before = None
        else:
            try:
                outside_before = read_handle(outside_handle)
            finally:
                kernel().CloseHandle(outside_handle)
        writer = run_child("write", target)
        replacer = run_child("replace", target, external, folder / "external.bak")
        assert outside_before in (None, ORIGINAL)
        assert not writer["success"] and not replacer["success"]
        if mode == "process-termination":
            process.kill()
            process.communicate(timeout=10)
            result = {
                "operation": "forced_process_termination",
                "exit_code": process.returncode,
            }
        else:
            output, stderr = process.communicate(mode + "\n", timeout=10)
            assert process.returncode == 0, stderr
            result = json.loads(output)
        after = target.read_bytes()
        assert after == (CANDIDATE if mode == "commit" else ORIGINAL)
        # Once commit/rollback has completed, the transaction must not linger.
        ordinary_writer = run_child("write", target)
        assert ordinary_writer["success"] and target.read_bytes() == EXTERNAL
        assert not (folder / "transaction.stage").exists()
        return {
            "mode": mode,
            "status": "PASS",
            "outside_read_before_commit": {
                "success": not outside_error,
                "winerror": outside_error,
                "old_bytes_if_readable": outside_before == ORIGINAL,
            },
            "child_writer": writer,
            "child_replacer": replacer,
            "end": result,
            "expected_final_content": "candidate" if mode == "commit" else "original",
            "ordinary_writer_after_end": ordinary_writer,
        }
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("Windows required")
    if args.child is not None:
        validate_child_paths([args.child])
        try:
            print(json.dumps(prepare_and_wait(args.child)), flush=True)
        except OSError as exc:
            print(
                json.dumps({"ready": False, "winerror": exc.errno, "step": str(exc)}),
                flush=True,
            )
        return
    parent = (
        Path(os.environ["LOCALAPPDATA"])
        / "PokeApp-migration-evidence"
        / "phase22-safety-resolution"
    )
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / ("txf-" + uuid.uuid4().hex)
    root.mkdir()
    cases = []
    for mode in ("commit", "rollback", "process-termination"):
        result = run_case(root, mode)
        cases.append(result)
        if result["status"] != "PASS":
            break
    status = (
        "PASS"
        if len(cases) == 3 and all(c["status"] == "PASS" for c in cases)
        else "UNAVAILABLE"
    )
    evidence = {
        "status": status,
        "utc": datetime.now(UTC).isoformat(),
        "windows": platform.platform(),
        "scope": "dummy NTFS files only; TxF feasibility, not certification",
        "cases": cases,
    }
    path = root / "txf-evidence.json"
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "cases": len(cases), "evidence": str(path)}))


if __name__ == "__main__":
    main()
