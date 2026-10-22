"""Prepare an isolated portable candidate; no game/owner data or launch authority."""

import argparse
import json
import shutil
from hashlib import sha256
from pathlib import Path

from app.launcher.emulator_qualification import (
    inspect_azahar_candidate,
    plain_local_path,
)


def prepare(executable, destination):
    candidate = inspect_azahar_candidate(executable)
    source = Path(candidate["path"]).parent
    parent = plain_local_path(destination.parent)
    target = parent / destination.name
    if target.exists() or target == source or source in target.parents:
        raise ValueError("FRESH_ISOLATED_DESTINATION_REQUIRED")
    # Fixed runtime surface; never copy installation user data, games or keys.
    inputs = [Path(candidate["path"]), *source.glob("*.dll")]
    plugins = source / "plugins"
    if plugins.exists():
        plain_local_path(plugins)
        inputs.extend(p for p in plugins.rglob("*") if p.is_file())
    for path in inputs:
        plain_local_path(path)
        if path.suffix.lower() not in {".dll", ".exe"}:
            raise ValueError("UNEXPECTED_RUNTIME_FILE")
    target.mkdir()
    (target / "user").mkdir()  # Azahar's supported portable directory seam.
    hashes = {}
    for path in inputs:
        output = target / path.relative_to(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        with path.open("rb") as original, output.open("xb") as copy:
            shutil.copyfileobj(original, copy)
        digest = sha256(output.read_bytes()).hexdigest()
        if digest != sha256(path.read_bytes()).hexdigest():
            raise ValueError("RUNTIME_COPY_CHANGED")
        hashes[str(path.relative_to(source))] = digest
    inspect_azahar_candidate(target / "azahar.exe")
    result = candidate | {
        "portable_root": str(target),
        "runtime_hashes": hashes,
        "games_copied": False,
        "user_data_copied": False,
        "launched": False,
    }
    (target / "qualification-preparation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--executable", type=Path, required=True)
    cli.add_argument("--destination", type=Path, required=True)
    args = cli.parse_args()
    print(json.dumps(prepare(args.executable, args.destination), indent=2))
