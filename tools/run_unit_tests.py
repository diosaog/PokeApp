"""Run normal unittest suites with disposable legacy data and no live credentials."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test*.py")
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    for name in list(os.environ):
        if name.upper().startswith(("SUPABASE", "POKEAPP_V2_SUPABASE", "POKEAPP_AUTH_PIN", "DISCORD")):
            os.environ.pop(name)
    os.environ["DISCORD_NOTIFICATIONS_ENABLED"] = "false"
    import streamlit
    import storage

    # Unlike the audit guard, this runs real SQLite operations in an empty temp DB.
    with tempfile.TemporaryDirectory(prefix="pokeapp-unittest-") as temp, ExitStack() as stack:
        root = Path(temp)
        stack.enter_context(patch.object(streamlit, "secrets", {}))
        stack.enter_context(patch.object(storage, "DATA_DIR", root))
        stack.enter_context(patch.object(storage, "SAVES_DIR", root / "saves"))
        stack.enter_context(patch.object(storage, "DB_PATH", root / "app.db"))
        connections = []
        original_connect = storage._conn

        def connect():
            connection = original_connect()
            connections.append(connection)
            return connection

        stack.enter_context(patch.object(storage, "_conn", connect))
        try:
            storage.init_storage()
            suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=args.pattern)
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        finally:
            for connection in connections:
                connection.close()
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
