"""Isolated NON-ATOMIC original-path handoff experiment; never a Launcher API.

New hypothesis: retain DELETE access on both files while denying write/delete
sharing, park the original by handle, then rename the candidate WITHOUT REPLACE.
An intervening creator wins safely: publication fails instead of overwriting it.
The original pathname is absent between renames, so this is NOT an atomic swap.
No product journal, capability, emulator adapter or economic receipt is changed.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import msvcrt
import os
import platform
import queue
import subprocess
import sys
import tempfile
import threading
from contextlib import ExitStack, contextmanager
from ctypes import wintypes
from hashlib import sha256
from pathlib import Path

from app.launcher.export_files import WindowsExportFiles
from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WindowsWriteFiles, _kernel
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.writer import PkhexProcessWriter
from tools.validate_phase22_export_engine import CASES

FILES = WindowsWriteFiles(process_names=list)
EXTERNAL = b"independent external change; must never be overwritten"


def digest(data):
    return sha256(data).hexdigest()


@contextmanager
def held(path):
    """Read+DELETE through this handle; no other writer/deleter may open it."""
    path = FILES.path(path)
    kernel = _kernel()
    handle = kernel.CreateFileW(str(path), 0x80010000, 1, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    fd = None
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        handle = None
        with os.fdopen(fd, "rb", buffering=0) as stream:
            fd = None
            if os.fstat(stream.fileno()).st_nlink != 1:
                raise RuntimeError("multiple_links")
            if WindowsExportFiles._handle_path(
                msvcrt.get_osfhandle(stream.fileno())
            ) != os.path.normcase(str(path)):
                raise RuntimeError("opened_path_changed")
            yield stream
    finally:
        if fd is not None:
            os.close(fd)
        if handle is not None:
            kernel.CloseHandle(handle)


def rename_no_replace(stream, destination):
    """Documented Win32 API, absolute path, FileRenameInfo, ReplaceIfExists=0."""

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
    ctypes.memmove(ctypes.addressof(payload) + Info.Name.offset, encoded, len(encoded))
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
        raise ctypes.WinError(ctypes.get_last_error())


def barrier(name):
    print(name, flush=True)
    if sys.stdin.readline().strip() != "NEXT":
        raise RuntimeError("probe_control_closed")


def checked_root(root):
    root = FILES.path(root, directory=True)
    if root.parent.parent != Path(
        tempfile.gettempdir()
    ).resolve() or not root.parent.name.startswith("phase22b-handoff-"):
        raise RuntimeError("owned_disposable_root_required")
    return root


def worker(root, mode):
    root = checked_root(root)
    manifest = json.loads((root / "probe.json").read_text())
    target, stage, parked = (
        root / name for name in ("original.save", "candidate.save", "parked.save")
    )
    with ExitStack() as stack:
        # Pin ancestors, but do NOT claim this prevents child-name creation.
        for parent in reversed(target.parents):
            handle = WindowsExportFiles._directory_handle(parent)
            stack.callback(WindowsExportFiles._close_directory_handle, handle)
        source = stack.enter_context(held(parked if mode == "recover" else target))
        if digest(FILES.read(source)) != manifest["original"]:
            raise RuntimeError("stale_source_or_recovery")
        if mode == "recover":
            rename_no_replace(source, target)
            print("RESTORED_ORIGINAL", flush=True)
            return
        candidate = stack.enter_context(held(stage))
        if digest(FILES.read(candidate)) != manifest["candidate"]:
            raise RuntimeError("stale_candidate")
        barrier("LOCKED")  # Last validation; independent attempts happen here.
        rename_no_replace(source, parked)
        barrier("PARKED")  # Intentional NON-ATOMIC interval; target is absent.
        rename_no_replace(candidate, target)
        barrier("PUBLISHED")  # Both handles are still held, including the new target.
        if (
            digest(FILES.read(candidate)) != manifest["candidate"]
            or digest(FILES.read(source)) != manifest["original"]
        ):
            raise RuntimeError("verification_failed")
        if WindowsExportFiles._handle_path(
            msvcrt.get_osfhandle(candidate.fileno())
        ) != os.path.normcase(str(target)):
            raise RuntimeError("published_path_changed")
        barrier("VERIFIED")
        print("PROBE_VERIFIED_NOT_PRODUCT_RECEIPT", flush=True)


def attack(root, mode):
    root = checked_root(root)
    target = root / "original.save"
    try:
        if mode == "write":
            kernel = _kernel()
            handle = kernel.CreateFileW(str(target), 0x40000000, 7, None, 2, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                fd = msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)
            except BaseException:
                kernel.CloseHandle(handle)
                raise
            with os.fdopen(fd, "wb", buffering=0) as output:
                output.write(EXTERNAL)
                output.flush()
                os.fsync(output.fileno())
        elif mode in ("replace", "rename_in"):
            incoming = root / "external.save"
            incoming.write_bytes(EXTERNAL)
            (os.replace if mode == "replace" else os.rename)(incoming, target)
        elif mode == "rename_out":
            os.rename(target, root / "external-moved.save")
        elif mode == "delete":
            target.unlink()
        else:
            raise ValueError("unknown_attack")
        print(json.dumps({"succeeded": True}))
    except OSError as error:
        print(json.dumps({"succeeded": False, "winerror": error.winerror}))


class Child:
    def __init__(self, root, mode="apply"):
        self.process = subprocess.Popen(
            command(root, mode),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.lines = queue.Queue()

        def drain():
            for line in self.process.stdout:
                self.lines.put(line.strip())
            self.lines.put("EOF")

        self.thread = threading.Thread(target=drain, daemon=True)
        self.thread.start()

    def expect(self, expected):
        actual = self.lines.get(timeout=20)
        if actual != expected:
            raise AssertionError(f"expected {expected}, got {actual}")

    def advance(self, expected):
        self.process.stdin.write("NEXT\n")
        self.process.stdin.flush()
        self.expect(expected)

    def finish(self):
        self.advance("PROBE_VERIFIED_NOT_PRODUCT_RECEIPT")
        self.process.wait(timeout=10)
        if self.process.returncode:
            raise AssertionError(self.process.stderr.read())

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=10)
        self.thread.join(timeout=2)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


def command(root, mode):
    return [
        sys.executable,
        "-m",
        "tools.phase22b_handoff_probe",
        "--worker",
        mode,
        "--root",
        str(root),
    ]


def child_result(root, mode):
    result = subprocess.run(
        command(root, mode),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def setup(root, name, original, candidate):
    case = root / name
    case.mkdir()
    for filename, data in (
        ("original.save", original),
        ("candidate.save", candidate),
        ("original.backup", original),
    ):
        FILES.create_verified(case / filename, data)
    (case / "probe.json").write_text(
        json.dumps({"original": digest(original), "candidate": digest(candidate)})
    )
    return case


def classify(case, original, candidate):
    """Read-only test oracle, NOT a replacement for product journal recovery."""
    target = case / "original.save"
    if target.exists():
        actual = target.read_bytes()
        if actual == original:
            return "ORIGINAL_PRESENT"
        if actual == candidate:
            return "CANDIDATE_PRESENT"
        return "CONFLICT"
    if (case / "parked.save").read_bytes() != original:
        return "CORRUPT_RECOVERY"
    return "RECOVERY_REQUIRED_PATH_ABSENT"


def run(native, fixtures, evidence):
    if evidence.exists():
        raise RuntimeError("evidence_must_be_new")
    manifest = json.loads(Path("tests/fixtures/phase21-public-saves.json").read_text())
    entries = {row["file"]: row for row in manifest["fixtures"]}
    parser, writer = PkhexProcessParser(native), PkhexProcessWriter(native)
    games, scenarios, source_hashes = [], [], {}
    with tempfile.TemporaryDirectory(prefix="phase22b-handoff-") as temp:
        root = Path(temp).resolve()
        for game, relative, location, expected, changed in CASES:
            original = (fixtures / relative).read_bytes()
            if (
                digest(original) != entries[relative]["sha256"]
                or len(original) != entries[relative]["bytes"]
            ):
                raise RuntimeError("fixture_manifest_mismatch")
            source_hashes[relative] = digest(original)
            observed = parser.parse(original)
            trainer = observed.trainer
            key = digest(
                "\0".join(
                    (
                        game,
                        trainer.name,
                        str(trainer.tid),
                        str(trainer.sid),
                        str(trainer.gender),
                        str(trainer.language),
                    )
                ).encode()
            )
            intent = WriteIntent.create(
                game=game,
                expected_sha256=digest(original),
                trainer_key=key,
                mutation={
                    "kind": "test_marking",
                    "location": location,
                    "box_index": 0 if location == "box" else None,
                    "slot_index": 0,
                    "expected_original": expected,
                    "new_value": changed,
                },
            )
            prepared = writer.prepare(original, intent)
            case = setup(root, game, original, prepared.output)
            child = Child(case)
            try:
                child.expect("LOCKED")
                child.advance("PARKED")
                if (case / "original.save").exists():
                    raise AssertionError("non_atomic_gap_not_observed")
                child.advance("PUBLISHED")
                child.advance("VERIFIED")
                child.finish()
            finally:
                child.close()
            persisted = (case / "original.save").read_bytes()
            writer.verify(original, persisted, intent, prepared)
            if parser.parse(persisted).model_dump(mode="json") != observed.model_dump(
                mode="json"
            ):
                raise AssertionError("unexpected_reader_diff")
            if (case / "parked.save").read_bytes() != original or (
                case / "original.backup"
            ).read_bytes() != original:
                raise AssertionError("original_not_preserved")
            games.append(
                {
                    "game": game,
                    "native_verified_at_original_path": True,
                    "original_preserved": True,
                    "source_sha256": digest(original),
                    "candidate_sha256": digest(persisted),
                }
            )
            if game == "X":
                x_original, x_candidate = original, prepared.output

        for point in ("LOCKED", "PARKED", "PUBLISHED"):
            modes = (
                ("write", "replace", "rename_in")
                if point == "PARKED"
                else ("write", "replace", "rename_out", "delete")
            )
            for mode in modes:
                case = setup(root, f"{point}-{mode}", x_original, x_candidate)
                child = Child(case)
                try:
                    child.expect("LOCKED")
                    if point != "LOCKED":
                        child.advance("PARKED")
                    if point == "PUBLISHED":
                        child.advance("PUBLISHED")
                    result = child_result(case, mode)
                    if point == "PARKED":
                        if not result["succeeded"]:
                            raise AssertionError("gap_contender_did_not_win")
                        child.advance("ERROR:183")
                        child.process.wait(timeout=10)
                        if (case / "original.save").read_bytes() != EXTERNAL:
                            raise AssertionError("external_change_lost")
                    else:
                        # MoveFileEx reports ACCESS_DENIED for a protected
                        # replacement target; CreateFile reports SHARING_VIOLATION.
                        if result["succeeded"] or result.get("winerror") not in (5, 32):
                            raise AssertionError(
                                f"guard_failure_{point}_{mode}_{result}"
                            )
                        if point == "LOCKED":
                            child.advance("PARKED")
                            child.advance("PUBLISHED")
                        child.advance("VERIFIED")
                        child.finish()
                finally:
                    child.close()
                if (case / "parked.save").read_bytes() != x_original or (
                    case / "original.backup"
                ).read_bytes() != x_original:
                    raise AssertionError("source_lost")
                scenarios.append(
                    {"name": f"{point}-{mode}", **result, "original_preserved": True}
                )

        for point in ("LOCKED", "PARKED", "PUBLISHED", "VERIFIED"):
            case = setup(root, f"kill-{point}", x_original, x_candidate)
            child = Child(case)
            try:
                child.expect("LOCKED")
                for reached in ("PARKED", "PUBLISHED", "VERIFIED"):
                    if point == "LOCKED":
                        break
                    child.advance(reached)
                    if point == reached:
                        break
            finally:
                child.close()  # Actual TerminateProcess, not a Python exception.
            state = classify(case, x_original, x_candidate)
            expected = {
                "LOCKED": "ORIGINAL_PRESENT",
                "PARKED": "RECOVERY_REQUIRED_PATH_ABSENT",
                "PUBLISHED": "CANDIDATE_PRESENT",
                "VERIFIED": "CANDIDATE_PRESENT",
            }[point]
            if (
                state != expected
                or (case / "original.backup").read_bytes() != x_original
            ):
                raise AssertionError("crash_state_mismatch")
            if point == "PARKED":
                recovered = subprocess.run(
                    command(case, "recover"),
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                if (
                    recovered.returncode
                    or recovered.stdout.strip() != "RESTORED_ORIGINAL"
                    or (case / "original.save").read_bytes() != x_original
                ):
                    raise AssertionError("recovery_failed")
            scenarios.append(
                {
                    "name": f"kill-{point}",
                    "classification": state,
                    "original_preserved": True,
                }
            )

        # Conflicts during restart must not be silently restored over.
        case = setup(root, "recovery-conflict", x_original, x_candidate)
        child = Child(case)
        try:
            child.expect("LOCKED")
            child.advance("PARKED")
        finally:
            child.close()
        (case / "original.save").write_bytes(EXTERNAL)
        recovered = subprocess.run(
            command(case, "recover"),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if (
            recovered.returncode != 2
            or "ERROR:183" not in recovered.stdout
            or (case / "original.save").read_bytes() != EXTERNAL
        ):
            raise AssertionError("recovery_overwrote_conflict")
        scenarios.append({"name": "recovery-conflict", "external_preserved": True})

        # Existing writer and competing Launcher-style process both deny entry.
        case = setup(root, "competing", x_original, x_candidate)
        with (case / "original.save").open("r+b"):
            denied = subprocess.run(
                command(case, "apply"),
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if denied.returncode != 2 or "ERROR:32" not in denied.stdout:
                raise AssertionError("existing_writer_not_denied")
        child = Child(case)
        try:
            child.expect("LOCKED")
            denied = subprocess.run(
                command(case, "apply"),
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if denied.returncode != 2 or "ERROR:32" not in denied.stdout:
                raise AssertionError("competing_process_not_denied")
            child.advance("PARKED")
            child.advance("PUBLISHED")
            child.advance("VERIFIED")
            child.finish()
        finally:
            child.close()
        replay = subprocess.run(
            command(case, "apply"),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if (
            replay.returncode != 2
            or "stale_source_or_recovery" not in replay.stdout
            or (case / "original.save").read_bytes() != x_candidate
        ):
            raise AssertionError("replay_not_rejected")
        scenarios.extend(
            {"name": name, "denied": True}
            for name in ("existing_writer", "competing_process", "replay")
        )
        for mode in ("write", "replace", "rename_out", "delete"):
            case = setup(root, f"unguarded-{mode}", x_original, x_candidate)
            result = child_result(case, mode)
            if not result["succeeded"]:
                raise AssertionError("unguarded_control_failed")
            scenarios.append({"name": f"unguarded-{mode}", "succeeded": True})

        for mode in ("stale_source", "stale_candidate", "occupied_park"):
            case = setup(root, mode, x_original, x_candidate)
            name = {
                "stale_source": "original.save",
                "stale_candidate": "candidate.save",
                "occupied_park": "parked.save",
            }[mode]
            (case / name).write_bytes(EXTERNAL)
            if mode == "occupied_park":
                child = Child(case)
                try:
                    child.expect("LOCKED")
                    child.advance("ERROR:183")
                    child.process.wait(timeout=10)
                finally:
                    child.close()
                if (case / "original.save").read_bytes() != x_original:
                    raise AssertionError("source_moved_despite_collision")
            else:
                denied = subprocess.run(
                    command(case, "apply"),
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                if denied.returncode != 2 or "stale_" not in denied.stdout:
                    raise AssertionError("stale_intent_not_denied")
            if (case / name).read_bytes() != EXTERNAL:
                raise AssertionError("conflict_overwritten")
            scenarios.append({"name": mode, "denied_preserved": True})

        case = setup(root, "corrupt-recovery", x_original, x_candidate)
        child = Child(case)
        try:
            child.expect("LOCKED")
            child.advance("PARKED")
        finally:
            child.close()
        (case / "parked.save").write_bytes(EXTERNAL)
        recovered = subprocess.run(
            command(case, "recover"),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if (
            recovered.returncode != 2
            or "stale_source_or_recovery" not in recovered.stdout
            or (case / "original.save").exists()
        ):
            raise AssertionError("corrupt_recovery_published")
        scenarios.append({"name": "corrupt-recovery", "denied": True})
        if any(
            digest((fixtures / name).read_bytes()) != expected
            for name, expected in source_hashes.items()
        ):
            raise AssertionError("fixture_source_changed")

    result = {
        "status": "PASS",
        "decision": "CONDITIONAL_NOT_ATOMIC",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "filesystem": "local NTFS",
        "games": games,
        "scenarios": scenarios,
        "scenario_count": len(scenarios),
        "fixture_hashes_unchanged": True,
        "temporary_root_removed": not root.exists(),
        "production_integration": False,
        "power_loss_tested": False,
        "real_emulator_tested": False,
        "journal_integration": False,
    }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"PASS: {len(games)} native games; {len(scenarios)} handoff scenarios; NON-ATOMIC, tools only"
    )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--worker")
    cli.add_argument("--root", type=Path)
    cli.add_argument("--native", type=Path)
    cli.add_argument("--fixtures", type=Path)
    cli.add_argument("--evidence", type=Path)
    args = cli.parse_args()
    if args.worker:
        try:
            if args.worker in ("apply", "recover"):
                worker(args.root, args.worker)
            else:
                attack(args.root, args.worker)
        except OSError as error:
            print(f"ERROR:{error.winerror}", flush=True)
            return 2
        except RuntimeError as error:
            print(f"ERROR:{error}", flush=True)
            return 2
    else:
        if not all((args.native, args.fixtures, args.evidence)):
            cli.error("--native, --fixtures and --evidence required")
        run(
            args.native.resolve(strict=True),
            args.fixtures.resolve(strict=True),
            args.evidence.resolve(),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
