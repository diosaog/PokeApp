"""Private pipe for the local Electron shell; never binds a TCP listener."""

import argparse
import json
import sys
from pathlib import Path

from app.launcher.backend import BackendClient
from app.launcher.config import state_directory
from app.launcher.core import LauncherLease
from app.launcher.runtime import PRODUCTION_API, LauncherRuntime
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.models import ErrorCode, SaveError


class UnavailableParser:
    """Backup history/copy remains local even if the optional worker is missing."""

    version = "unavailable"

    def parse(self, data):
        raise SaveError(ErrorCode.PARSER_FAILURE)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--profile", type=Path)
    cli.add_argument("--parser", type=Path, required=True)
    cli.add_argument("--backend", default=PRODUCTION_API)
    args = cli.parse_args()
    profile = args.profile or state_directory()
    try:
        parser = PkhexProcessParser(args.parser)
    except (OSError, ValueError):
        parser = UnavailableParser()
    with LauncherLease(profile):
        runtime = LauncherRuntime(
            profile,
            SaveInspector(parser),
            client=BackendClient(args.backend),
        )
        try:
            for line in sys.stdin:
                identifier = None
                try:
                    if len(line) > 16384:
                        raise ValueError("oversize_command")
                    command = json.loads(line)
                    identifier = command["id"]
                    value = runtime.command(command["command"], command.get("args"))
                    result = {"id": identifier, "result": value}
                except Exception:  # noqa: BLE001 - sanitized pipe boundary, never return secrets
                    result = {"id": identifier, "error": "LAUNCHER_REQUEST_FAILED"}
                print(json.dumps(result, ensure_ascii=True), flush=True)
        finally:
            runtime.close()


if __name__ == "__main__":
    main()
