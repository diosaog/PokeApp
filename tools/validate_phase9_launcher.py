"""Build the pinned worker; generated binary, IPC, local sync and Windows checks.

No credentials, personal saves, network API or database server. Package restore
uses NuGet with a locked dependency; --dotnet selects a local SDK installation.
"""
# ruff: noqa: E402 -- direct script entry point adds the repository root first.

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.launcher.config import LauncherConfig
from app.launcher.core import LauncherCore, LauncherLease
from app.launcher.discovery import FolderProvider, SaveDiscoveryService
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.files import SaveSource, SnapshotReader
from app.save_parser.models import ErrorCode, SaveError


def windows_lock_check(path: Path):
    if os.name != "nt":
        print("Windows share-mode check not applicable on this OS")
        return
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
    source = SaveSource.enroll(path)
    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError("could_not_create_exclusive_test_handle")
    try:
        try:
            SnapshotReader().read(source)
        except SaveError as exc:
            assert exc.code == ErrorCode.FILE_LOCKED, exc.code
        else:
            raise AssertionError("locked_file_accepted")
    finally:
        kernel.CloseHandle(handle)
    SnapshotReader().read(source)
    print("PASS real Windows exclusive handle rejects read; recovery after close")


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--dotnet", default="dotnet")
    args = cli.parse_args()
    dotnet = (
        str(Path(args.dotnet).resolve()) if Path(args.dotnet).exists() else args.dotnet
    )
    project = (
        ROOT / "companion/parser/PokeApp.Parser.Checks/PokeApp.Parser.Checks.csproj"
    )
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    subprocess.run(
        [dotnet, "restore", str(project), "--locked-mode", "--nologo"],
        check=True,
        cwd=ROOT,
        env=env,
    )
    with tempfile.TemporaryDirectory(prefix="pokeapp-phase9-") as folder:
        temp = Path(folder)
        fixtures = temp / "fixtures"
        subprocess.run(
            [
                dotnet,
                "run",
                "--project",
                str(project),
                "-c",
                "Release",
                "--no-restore",
                "--",
                str(fixtures),
            ],
            check=True,
            cwd=ROOT,
            env=env,
        )
        executable = (
            ROOT
            / "companion/parser/PokeApp.Parser/bin/Release/net8.0"
            / ("PokeApp.Parser.exe" if os.name == "nt" else "PokeApp.Parser")
        )
        # Portable SDK installs need their matching runtime when the host lacks it.
        runtime = Path(dotnet).parent
        if runtime.is_absolute():
            os.environ["DOTNET_ROOT"] = str(runtime)
        parser = PkhexProcessParser(executable)
        inspector = SaveInspector(parser)
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in fixtures.glob("*.sav")
        }
        for generation in (3, 4, 5):
            path = fixtures / f"gen{generation}.sav"
            parsed = inspector.inspect(SaveSource.enroll(path))
            assert parsed.observation.generation == generation
            assert len(parsed.observation.identity_observations()) == 2
            assert parsed.observation.progress is not None
            assert parsed.observation.progress.regions[0].badge_flags == (False,) * 8
        print(
            "PASS real byte IPC, strict neutral DTO and live-file verification Gen3/4/5"
        )
        regional = inspector.inspect(
            SaveSource.enroll(fixtures / "progress/hgss-kanto-only.sav")
        )
        assert regional.observation.progress.primary_region == "johto"
        assert regional.observation.progress.regions[0].badge_flags == (False,) * 8
        assert regional.observation.progress.regions[1].badge_flags == (True,) * 8
        assert regional.parser_version == "pokeapp-reader/2;pkhex/24.11.11"
        print(
            "PASS regional observed progress across real HGSS byte IPC; unknown never inferred"
        )
        local = temp / "Espacio Pokémon.sav"
        local.write_bytes((fixtures / "gen5.sav").read_bytes())
        profile = temp / "profile"
        with LauncherLease(profile):
            core = LauncherCore(profile, inspector)
            core.select(local)
            first = core.manual_sync()
            assert first.status == "SYNCED"
            assert core.manual_sync().status == "NO_CHANGE"
            restarted = LauncherCore(profile, inspector)
            assert restarted.manual_sync().receipt_id == first.receipt_id
            ticket = restarted.backup()
            restarted.backups.verify(ticket)
            assert restarted.queue.get(ticket.operation_id)["status"] == "SUCCESS"
            local.write_bytes((fixtures / "gen4.sav").read_bytes())
            restarted.config = LauncherConfig.model_validate(
                restarted.config.model_dump() | {"auto_sync": True}
            )
            watch = restarted.watcher()
            assert watch.tick(0) is None
            assert watch.tick(1).status == "SYNCED"
            head = restarted.journal.head(SaveSource.enroll(local))
            assert head.observation.generation == 4
            local.write_bytes(b"truncated")
            assert restarted.manual_sync().status == "INVALID"
            assert restarted.journal.head(SaveSource.enroll(local)).id == head.id
            local.write_bytes((fixtures / "gen4.sav").read_bytes())
            assert restarted.manual_sync().status == "NO_CHANGE"
        print(
            "PASS real local manual/automatic sync, idempotency, restart, backup and invalid-save recovery"
        )
        result = SaveDiscoveryService().discover((FolderProvider(fixtures),))
        assert len(result.candidates) == 3 and not result.errors
        windows_lock_check(local)
        command = [
            sys.executable,
            "-m",
            "app.launcher",
            "--profile",
            str(profile),
            "--parser",
            str(executable),
        ]
        for extra in (["status"], ["inspect", str(local)], ["sync"]):
            run = subprocess.run(
                command + extra,
                cwd=ROOT,
                env=os.environ.copy(),
                capture_output=True,
                check=True,
            )
            result = json.loads(run.stdout)
            if extra[0] == "status":
                assert result["cloud_sync"] == "NOT_CONFIGURED"
            else:
                assert result["status"] in ("INSPECTED", "NO_CHANGE")
        print("PASS CLI status/inspect/sync over real worker and Unicode paths")
        assert before == {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in fixtures.glob("*.sav")
        }
        print(
            "PASS synthetic input saves unchanged; all profile/fixtures isolated in temporary directory"
        )
    print("RESULT OK; Phase 9 generated binary and Launcher integration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
