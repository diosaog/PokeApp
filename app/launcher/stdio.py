"""Private pipe for the local Electron shell; never binds a TCP listener.

Answers carry the request id. Lines without one are lifecycle events for the
shell's supervisor: {"event": "core", "status": STARTING | WAITING_PREVIOUS |
READY | FATAL, ...}. A core that cannot start says why (FATAL + code) and
exits with a non-zero code instead of leaving the shell waiting.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import threading
import time
import traceback
from pathlib import Path

from app.launcher.backend import BackendClient
from app.launcher.config import state_directory
from app.launcher.core import LauncherLease
from app.launcher.diagnostics import close_core_log, core_log, failure, mask
from app.launcher.journal import LocalConflict
from app.launcher.runtime import PRODUCTION_API, LauncherRuntime
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.models import ErrorCode, SaveError

# A previous core that is still finishing keeps the profile until its last
# step ends (its window was just closed, or an update restarted the Launcher):
# waiting for it is always safe; starting beside it never is.
LEASE_WAIT_SECONDS = 120
# Commands that can take seconds run beside the pipe, so `state` keeps
# answering meanwhile (answers are matched by id, in any order).
BACKGROUND_COMMANDS = ("discover_saves",)
EXIT_ALREADY_RUNNING, EXIT_STARTUP_FAILED = 3, 4


def error_code(exc):
    """A refusal's own code (ValueError("invalid_selection") → INVALID_SELECTION)
    so the shell can explain it; anything else stays generic. Never a message,
    path or secret."""
    text = str(exc) if isinstance(exc, (ValueError, LookupError)) else ""
    if re.fullmatch(r"[a-z][a-z_]{2,63}", text):
        return text.upper()
    return "LAUNCHER_REQUEST_FAILED"


def startup_code(exc):
    """Why the core could not start, as a stable code the shell explains."""
    if isinstance(exc, LocalConflict):
        return str(exc)
    if isinstance(exc, sqlite3.Error) or str(exc) in (
        "unsupported_local_schema",
        "journal_symlink_denied",
    ):
        return "LOCAL_DATA_UNREADABLE"
    if isinstance(exc, PermissionError):
        return "PROFILE_ACCESS_DENIED"
    if str(exc) == "local_directory_required":
        return "PROFILE_UNAVAILABLE"
    return "STARTUP_FAILED"


class UnavailableParser:
    """Backup history/copy remains local even if the optional worker is missing."""

    version = "unavailable"

    def parse(self, data):
        raise SaveError(ErrorCode.PARSER_FAILURE)


class Pipe:
    """One line per message; answers from background commands never interleave."""

    def __init__(self, stream):
        self._stream, self._lock = stream, threading.Lock()

    def send(self, message):
        line = json.dumps(message, ensure_ascii=True)
        with self._lock:
            print(line, file=self._stream, flush=True)

    def event(self, status, **fields):
        self.send({"event": "core", "status": status, **fields})


def answer(runtime, pipe, identifier, name, args):
    try:
        result = {"id": identifier, "result": runtime.command(name, args)}
    except Exception as exc:  # noqa: BLE001 - sanitized pipe boundary, never return secrets
        result = {"id": identifier, "error": error_code(exc)}
    pipe.send(result)


def serve(runtime, lines, pipe):
    busy = {name: threading.Lock() for name in BACKGROUND_COMMANDS}
    for line in lines:
        identifier = None
        try:
            if len(line) > 16384:
                raise ValueError("oversize_command")
            command = json.loads(line)
            identifier = command["id"]
            name, args = command["command"], command.get("args")
            if name not in busy:
                answer(runtime, pipe, identifier, name, args)
                continue
            if not busy[name].acquire(blocking=False):
                pipe.send({"id": identifier, "result": {"status": "BUSY"}})
                continue

            def run(lock=busy[name], identifier=identifier, name=name, args=args):
                try:
                    answer(runtime, pipe, identifier, name, args)
                finally:
                    lock.release()

            threading.Thread(target=run, daemon=True).start()
        except Exception as exc:  # noqa: BLE001 - sanitized pipe boundary
            pipe.send({"id": identifier, "error": error_code(exc)})


def main():
    try:
        return run()
    finally:
        close_core_log()


def run():
    cli = argparse.ArgumentParser()
    cli.add_argument("--profile", type=Path)
    cli.add_argument("--parser", type=Path, required=True)
    cli.add_argument("--backend", default=PRODUCTION_API)
    args = cli.parse_args()
    pipe = Pipe(sys.stdout)
    started = time.monotonic()
    pipe.event("STARTING", pid=os.getpid())
    log = None
    try:
        profile = args.profile or state_directory()
        log = core_log(profile)
        log.info("STARTING pid=%s", os.getpid())
        try:
            parser = PkhexProcessParser(args.parser)
        except (OSError, ValueError) as exc:
            log.warning("PARSER_UNAVAILABLE %s", failure(exc))
            parser = UnavailableParser()

        def waiting():
            log.info("WAITING_PREVIOUS: another core still holds this profile")
            pipe.event("WAITING_PREVIOUS")

        lease = LauncherLease(profile, wait=LEASE_WAIT_SECONDS, on_wait=waiting)
        lease.__enter__()
    except Exception as exc:  # noqa: BLE001 - reported as a code; details stay in the local log
        code = startup_code(exc)
        if log is not None:
            log.error("FATAL %s %s\n%s", code, failure(exc), mask(traceback.format_exc()))
        pipe.event("FATAL", code=code)
        return EXIT_ALREADY_RUNNING if code == "LAUNCHER_ALREADY_RUNNING" else EXIT_STARTUP_FAILED
    try:
        try:
            runtime = LauncherRuntime(
                profile,
                SaveInspector(parser),
                client=BackendClient(args.backend),
                discover=True,
                log=log,
            )
        except Exception as exc:  # noqa: BLE001 - reported as a code
            code = startup_code(exc)
            log.error("FATAL %s %s\n%s", code, failure(exc), mask(traceback.format_exc()))
            pipe.event("FATAL", code=code)
            return EXIT_STARTUP_FAILED
        seconds = round(time.monotonic() - started, 2)
        log.info(
            "READY in %ss%s", seconds, " (unreadable config.json set aside)" if runtime.core.config_reset else ""
        )
        pipe.event("READY", seconds=seconds, config_reset=runtime.core.config_reset)
        try:
            serve(runtime, sys.stdin, pipe)
        finally:
            log.info("STOPPING: the Launcher closed the pipe")
            runtime.close()
            log.info("STOPPED")
    finally:
        lease.__exit__(None, None, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
