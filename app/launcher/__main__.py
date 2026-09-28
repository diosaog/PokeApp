"""Development entry point for the UI-free Launcher base (not the final installer)."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from getpass import getpass
import json
from pathlib import Path
import time

from app.launcher.backend import BackendClient, BackendError, LauncherSession
from app.launcher.config import LauncherConfig, state_directory, local_directory
from app.launcher.core import LauncherCore, LauncherLease
from app.launcher.discovery import FolderProvider, SaveDiscoveryService
from app.launcher.journal import LocalConflict
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.files import SaveSource
from app.save_parser.models import SaveError


def output(value):
    print(json.dumps(value, ensure_ascii=False))


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="PokeApp Launcher core — local observation mode"
    )
    cli.add_argument("--profile", type=Path, help="Local configuration/state directory")
    cli.add_argument(
        "--parser", type=Path, help="Locally installed PokeApp.Parser executable"
    )
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("discover")
    commands.add_parser("status")
    commands.add_parser("sync")
    commands.add_parser("backup")
    commands.add_parser("watch")
    commands.add_parser("select").add_argument("path", type=Path)
    commands.add_parser("add-folder").add_argument("path", type=Path)
    commands.add_parser("inspect").add_argument("path", type=Path)
    login = commands.add_parser("login")
    login.add_argument("--backend", required=True)
    login.add_argument("--trainer", required=True)
    args = cli.parse_args(argv)
    try:
        profile = (
            local_directory(args.profile, create=True)
            if args.profile
            else state_directory()
        )
        with LauncherLease(profile):
            config_path = profile / "config.json"
            config = LauncherConfig.load(config_path)
            if args.command == "select":
                source = SaveSource.enroll(args.path)
                config = LauncherConfig.model_validate(
                    config.model_dump() | {"selected_save": str(source.path)}
                )
                config.save(config_path)
                output({"status": "SELECTED"})
                return 0
            if args.command == "add-folder":
                folder = str(local_directory(args.path))
                config = LauncherConfig.model_validate(
                    config.model_dump()
                    | {"folders": tuple(sorted(set(config.folders) | {folder}))}
                )
                config.save(config_path)
                output({"status": "CONFIGURED"})
                return 0
            if args.command == "discover":
                result = SaveDiscoveryService().discover(
                    tuple(FolderProvider(Path(p)) for p in config.folders)
                )
                # This is explicit local discovery output, never a support log or backend request.
                output(
                    {
                        "candidates": [str(s.path) for s in result.candidates],
                        "errors": result.errors,
                    }
                )
                return 0
            if args.command == "status":
                output(
                    {
                        "selected": bool(config.selected_save),
                        "auto_sync": config.auto_sync,
                        "destination": "LOCAL_OBSERVATION_JOURNAL",
                        "cloud_sync": "NOT_CONFIGURED",
                    }
                )
                return 0
            if args.command == "login":
                client = BackendClient(args.backend)
                try:
                    session = LauncherSession(client)
                    principal = session.login(args.trainer, getpass("PIN PokeApp: "))
                    config = LauncherConfig.model_validate(
                        config.model_dump() | {"backend_url": client.origin}
                    )
                    config.save(config_path)
                    output(
                        {
                            "status": "AUTHENTICATED",
                            "trainer_id": principal.trainer_id,
                            "session_persistence": "MEMORY_ONLY",
                        }
                    )
                    session.logout()
                finally:
                    client.close()
                return 0
            if args.parser is None:
                raise ValueError("parser_required")
            inspector = SaveInspector(PkhexProcessParser(args.parser))
            if args.command == "inspect":
                result = inspector.inspect(SaveSource.enroll(args.path))
                output(
                    dict(
                        status="INSPECTED",
                        game=result.observation.game,
                        generation=result.observation.generation,
                        pokemon=len(tuple(result.observation.occupied())),
                        fingerprint=result.snapshot.fingerprint.model_dump(),
                        parser_version=result.parser_version,
                    )
                )
                return 0
            core = LauncherCore(profile, inspector)
            core.queue.recover_interrupted()  # single profile lease held above
            if args.command == "sync":
                result = core.manual_sync()
                output(asdict(result))
                return 0 if result.status in ("SYNCED", "NO_CHANGE") else 1
            if args.command == "backup":
                ticket = core.backup()
                output(
                    {
                        "status": "BACKUP_VERIFIED",
                        "backup_id": ticket.backup_id,
                        "operation_id": ticket.operation_id,
                    }
                )
                return 0
            core.config = LauncherConfig.model_validate(
                config.model_dump() | {"auto_sync": True}
            )
            core.config.save(config_path)
            watch = core.watcher()
            while True:
                result = watch.tick(time.monotonic())
                if result and result.status != "NO_CHANGE":
                    output(asdict(result))
                time.sleep(0.25)
    except (SaveError, BackendError, LocalConflict) as exc:
        output({"status": "ERROR", "error": str(exc)})
        return 1
    except (OSError, ValueError):
        output({"status": "ERROR", "error": "LOCAL_CONFIGURATION_INVALID"})
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
