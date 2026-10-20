"""Isolated Windows sharing/rename probe; never accepts an existing save path.

Only newly created dummy files below a fresh evidence directory are touched.
Child processes use ordinary Win32 APIs and do not cooperate with app locks.
No parser, real save, package, production endpoint, or old test matrix is used.
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

READ, WRITE, DELETE = 0x80000000, 0x40000000, 0x10000
INVALID = ctypes.c_void_p(-1).value
ORIGINAL, EXTERNAL, CANDIDATE = b"ORIGINAL", b"EXTERNAL", b"PROPOSED"


def probe_parent():
    return (
        Path(os.environ["LOCALAPPDATA"])
        / "PokeApp-migration-evidence"
        / "phase22-safety-resolution"
    )


def validate_child_paths(paths):
    """Internal subprocess arguments remain inside generated dummy-run folders."""
    for item in paths:
        path = Path(item).resolve()
        relative = path.relative_to(probe_parent().resolve())
        if len(relative.parts) != 3:
            raise ValueError("Only generated dummy paths are accepted")
        prefix, _, suffix = relative.parts[0].partition("-")
        if prefix not in ("sharing", "txf") or len(suffix) != 32:
            raise ValueError("Unknown dummy run directory")
        int(suffix, 16)
        if path.suffix not in (".bin", ".bak"):
            raise ValueError("Only dummy probe files are accepted")


def kernel():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateFileW": (
            [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE],
            w.HANDLE,
        ),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "ReplaceFileW": (
            [w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, w.DWORD, w.LPVOID, w.LPVOID],
            w.BOOL,
        ),
        "MoveFileExW": ([w.LPCWSTR, w.LPCWSTR, w.DWORD], w.BOOL),
        "SetFileInformationByHandle": ([w.HANDLE, w.INT, w.LPVOID, w.DWORD], w.BOOL),
        "ReadFile": (
            [w.HANDLE, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID],
            w.BOOL,
        ),
        "WriteFile": (
            [w.HANDLE, w.LPCVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID],
            w.BOOL,
        ),
        "CreateFileMappingW": (
            [w.HANDLE, w.LPVOID, w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR],
            w.HANDLE,
        ),
        "MapViewOfFile": (
            [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.c_size_t],
            w.LPVOID,
        ),
        "FlushViewOfFile": ([w.LPCVOID, ctypes.c_size_t], w.BOOL),
        "UnmapViewOfFile": ([w.LPCVOID], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        getattr(k, name).argtypes = args
        getattr(k, name).restype = result
    return k


def opened(path, access=READ, sharing=1):
    ctypes.set_last_error(0)
    h = kernel().CreateFileW(str(path), access, sharing, None, 3, 0x00200000, None)
    return h, ctypes.get_last_error() if h == INVALID else 0


def outcome(result):
    return {
        "success": bool(result),
        "winerror": 0 if result else ctypes.get_last_error(),
    }


def replace(target, stage, witness):
    ctypes.set_last_error(0)
    return outcome(
        kernel().ReplaceFileW(str(target), str(stage), str(witness), 0, None, None)
    )


def rename_handle(source, destination, *, replace_existing=True, extended=False):
    class Rename(ctypes.Structure):
        _fields_ = [
            ("Flags", w.DWORD),
            ("RootDirectory", w.HANDLE),
            ("FileNameLength", w.DWORD),
            ("FileName", w.WCHAR * 1),
        ]

    h, error = opened(source, READ | DELETE, 7)
    if error:
        return {"success": False, "winerror": error, "stage": "open"}
    try:
        raw = str(destination).encode("utf-16-le")
        buf = ctypes.create_string_buffer(Rename.FileName.offset + len(raw) + 2)
        info = Rename.from_buffer(buf)
        info.Flags = 3 if extended else int(replace_existing)
        info.FileNameLength = len(raw)
        ctypes.memmove(ctypes.addressof(buf) + Rename.FileName.offset, raw, len(raw))
        ctypes.set_last_error(0)
        return outcome(
            kernel().SetFileInformationByHandle(h, 22 if extended else 3, buf, len(buf))
        )
    finally:
        kernel().CloseHandle(h)


def read_handle(h):
    data, count = ctypes.create_string_buffer(32), w.DWORD()
    assert kernel().ReadFile(h, data, 32, ctypes.byref(count), None)
    return data.raw[: count.value]


def child(action, paths):
    k = kernel()
    target = Path(paths[0])
    if action == "write":
        h, error = opened(target, WRITE, 7)
        if error:
            return {"success": False, "winerror": error}
        try:
            count = w.DWORD()
            return outcome(
                k.WriteFile(h, EXTERNAL, len(EXTERNAL), ctypes.byref(count), None)
            )
        finally:
            k.CloseHandle(h)
    if action == "move":
        return outcome(k.MoveFileExW(str(target), paths[1], 0))
    if action == "replace":
        return replace(target, *paths[1:])
    if action in ("rename", "rename-posix"):
        return rename_handle(target, paths[1], extended=action == "rename-posix")
    if action == "mapped":
        h, error = opened(target, READ | WRITE, 7)
        assert not error
        mapping = k.CreateFileMappingW(h, None, 4, 0, 0, None)  # PAGE_READWRITE
        assert mapping
        view = k.MapViewOfFile(mapping, 2, 0, 0, 0)  # FILE_MAP_WRITE
        assert view
        # Keep only a mapped view: no ordinary writer handle remains open.
        k.CloseHandle(mapping)
        k.CloseHandle(h)
        print(json.dumps({"ready": True, "pid": os.getpid()}), flush=True)
        assert sys.stdin.readline().strip() == "mutate"
        ctypes.memmove(view, EXTERNAL, len(EXTERNAL))
        flushed = outcome(k.FlushViewOfFile(view, len(EXTERNAL)))
        k.UnmapViewOfFile(view)
        return flushed
    raise ValueError("Unknown child action")


def run_child(action, *paths):
    result = subprocess.run(
        [sys.executable, __file__, "--child", action, *(str(p) for p in paths)],
        check=True,
        text=True,
        capture_output=True,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    data = json.loads(result.stdout)
    assert data["pid"] != os.getpid()
    return data


def fixtures(root, name):
    directory = root / name
    directory.mkdir()
    paths = [
        directory / x
        for x in (
            "original.bin",
            "external.bin",
            "candidate.bin",
            "external.bak",
            "candidate.bak",
        )
    ]
    for p, data in zip(paths, (ORIGINAL, EXTERNAL, CANDIDATE)):
        p.write_bytes(data)
    return paths


def probe(root):
    k, records = kernel(), []

    # Strict share-deny is mandatory for other normal opens, including ours.
    t, ext, candidate, ext_backup, own_backup = fixtures(root, "strict")
    handle, error = opened(t)
    assert not error
    try:
        results = {
            "child_write": run_child("write", t),
            "child_move": run_child("move", t, t.with_name("moved.bin")),
            "child_replace": run_child("replace", t, ext, ext_backup),
            "own_replace": replace(t, candidate, own_backup),
            "child_handle_rename": run_child("rename", ext, t),
        }
        assert all(not x["success"] for x in results.values())
        assert t.read_bytes() == ORIGINAL
        records.append(
            {
                "case": "deny_write_delete_blocks_normal_apis_and_own_replace",
                "results": results,
            }
        )
    finally:
        k.CloseHandle(handle)

    # With delete sharing, the pathname can change while our old handle lives.
    t, ext, candidate, ext_backup, own_backup = fixtures(root, "delete-sharing")
    handle, error = opened(t, sharing=5)
    assert not error
    try:
        external = run_child("replace", t, ext, ext_backup)
        assert external["success"] and t.read_bytes() == EXTERNAL
        assert read_handle(handle) == ORIGINAL
        own = replace(t, candidate, own_backup)
        assert own["success"]
        assert t.read_bytes() == CANDIDATE and own_backup.read_bytes() == EXTERNAL
        records.append(
            {
                "case": "delete_sharing_allows_external_replace_then_our_overwrite",
                "external": external,
                "own": own,
                "old_handle_kept_original": True,
                "external_bytes_only_in_witness": True,
            }
        )
    finally:
        k.CloseHandle(handle)

    # Releasing strict handle for our ReplaceFile creates a reproducible window.
    t, ext, candidate, ext_backup, own_backup = fixtures(root, "release-gap")
    handle, error = opened(t)
    assert not error and read_handle(handle) == ORIGINAL
    k.CloseHandle(handle)
    external = run_child("replace", t, ext, ext_backup)
    own = replace(t, candidate, own_backup)
    assert external["success"] and own["success"]
    assert t.read_bytes() == CANDIDATE and own_backup.read_bytes() == EXTERNAL
    records.append(
        {"case": "strict_handle_release_reopens_gap", "external": external, "own": own}
    )

    # Source-by-handle does not turn replacement destination into a CAS.
    t, ext, candidate, ext_backup, _ = fixtures(root, "handle-replace")
    handle, error = opened(t)
    assert not error
    blocked = rename_handle(candidate, t)
    assert not blocked["success"]
    k.CloseHandle(handle)
    external = run_child("replace", t, ext, ext_backup)
    own = rename_handle(candidate, t)
    assert external["success"] and own["success"] and t.read_bytes() == CANDIDATE
    records.append(
        {
            "case": "handle_source_rename_target_still_named_not_cas",
            "blocked": blocked,
            "external": external,
            "own": own,
        }
    )

    # Observe POSIX rename explicitly rather than extrapolating from old rename.
    t, ext, _, _, _ = fixtures(root, "posix-rename")
    handle, error = opened(t)
    assert not error
    try:
        result = run_child("rename-posix", ext, t)
        records.append(
            {
                "case": "posix_handle_rename_against_no_delete_sharing",
                "result": result,
                "original_at_path": t.read_bytes() == ORIGINAL,
            }
        )
    finally:
        k.CloseHandle(handle)

    # Existing writable mappings need separate proof from ordinary open handles.
    t, _, _, _, _ = fixtures(root, "mapped-view")
    process = subprocess.Popen(
        [sys.executable, __file__, "--child", "mapped", str(t)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    handle = None
    try:
        ready = json.loads(process.stdout.readline())
        assert ready["ready"] and ready["pid"] != os.getpid()
        handle, error = opened(t)
        process.stdin.write("mutate\n")
        process.stdin.flush()
        output, stderr = process.communicate(timeout=15)
        assert process.returncode == 0, stderr
        mutation = json.loads(output)
        records.append(
            {
                "case": "preexisting_writable_mapping_with_file_handles_closed",
                "read_handle_open_success": not error,
                "read_handle_open_error": error,
                "child_mutation": mutation,
                "path_changed_externally": t.read_bytes() == EXTERNAL,
            }
        )
    finally:
        if handle not in (None, INVALID):
            k.CloseHandle(handle)
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    # Nonreplacement handle rename refuses a competing destination atomically.
    t, ext, candidate, ext_backup, _ = fixtures(root, "no-replace")
    external = run_child("replace", t, ext, ext_backup)
    refused = rename_handle(candidate, t, replace_existing=False)
    assert external["success"] and not refused["success"]
    assert t.read_bytes() == EXTERNAL and candidate.read_bytes() == CANDIDATE
    records.append(
        {
            "case": "no_replace_rename_preserves_existing_destination",
            "external": external,
            "refused": refused,
        }
    )
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--child",
        choices=("write", "move", "replace", "rename", "rename-posix", "mapped"),
    )
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("This probe requires Windows.")
    if args.child:
        validate_child_paths(args.paths)
        result = child(args.child, args.paths)
        print(json.dumps({**result, "pid": os.getpid()}), flush=True)
        return
    if args.paths:
        raise SystemExit("Existing paths are not accepted.")
    parent = probe_parent()
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / ("sharing-" + uuid.uuid4().hex)
    root.mkdir()
    records = probe(root)
    evidence = {
        "status": "PASS",
        "utc": datetime.now(UTC).isoformat(),
        "windows": platform.platform(),
        "python": platform.python_version(),
        "parent_pid": os.getpid(),
        "scope": "fresh dummy files only; no saves/production/native gates",
        "cases": records,
    }
    path = root / "sharing-evidence.json"
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "cases": len(records), "evidence": str(path)}))


if __name__ == "__main__":
    main()
