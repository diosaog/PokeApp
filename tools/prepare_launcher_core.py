"""Narrow build overlay: keep backend domain barrel imports out of the desktop."""

import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def prepare(output):
    if output.exists():
        raise RuntimeError("Use a fresh source overlay directory")
    (output / "app/domain").mkdir(parents=True)
    for group in ("launcher", "save_parser"):
        target = output / "app" / group
        target.mkdir()
        for source in (REPO / "app" / group).glob("*.py"):
            shutil.copy2(source, target / source.name)
    # These packages expose only the explicitly imported desktop contracts.
    for relative in ("app/__init__.py", "app/domain/__init__.py"):
        (output / relative).write_text('"""Launcher distribution namespace."""\n', encoding="utf-8")
    shutil.copy2(REPO / "app/domain/pokemon_identity.py", output / "app/domain/pokemon_identity.py")
    shutil.copy2(REPO / "companion/launcher/core-entry.py", output / "core-entry.py")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("output", type=Path)
    prepare(cli.parse_args().output)
