"""Import the FastAPI app as Linux would: no Windows-only modules.

The API ships in a Linux container (Railway), but the suites run on Windows,
where msvcrt, winreg and ctypes.windll exist. This loads ``app.api.main`` with
those blocked and ``sys.platform`` set to linux, so a Windows-only import on
the API's path fails here instead of in production.

Run: python -m tools.check_api_portable_imports
"""

from __future__ import annotations

import ctypes
import importlib
import importlib.abc
import os
import sys

# Only what application code could import; the stdlib on this host needs
# _winapi/_overlapped itself.
WINDOWS_ONLY = {"msvcrt", "winreg", "winsound", "_msi"}


class _Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in WINDOWS_ONLY:
            raise ModuleNotFoundError(
                f"No module named '{name}' (blocked: Linux has no Windows modules)"
            )


def main() -> int:
    # The stdlib detects Windows by importing msvcrt (subprocess, getpass…):
    # load it first, so the block below only judges application imports.
    for module in (
        "subprocess",
        "getpass",
        "asyncio",
        "multiprocessing",
        "tempfile",
        "uuid",
    ):
        importlib.import_module(module)

    for name in WINDOWS_ONLY:
        sys.modules.pop(name, None)
    sys.meta_path.insert(0, _Block())
    for attribute in (
        "windll",
        "oledll",
        "WinDLL",
        "OleDLL",
        "WINFUNCTYPE",
        "FormatError",
        "GetLastError",
    ):
        if hasattr(ctypes, attribute):
            delattr(ctypes, attribute)
    for name in list(os.environ):
        if name.upper().startswith(("SUPABASE", "POKEAPP_V2_SUPABASE")):
            os.environ.pop(name)
    from app.api.main import app

    print("API imports without Windows modules:", len(app.openapi()["paths"]), "routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
