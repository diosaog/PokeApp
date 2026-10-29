"""Frozen stdio entry point; keep the console subsystem for private IPC pipes."""

import sys

from app.launcher.stdio import main

if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    # The exit code tells the Launcher why a core could not start.
    sys.exit(main())
