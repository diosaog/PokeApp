"""Fail closed on unexpected application payloads; runtime and release manifest."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

REPO = Path(__file__).resolve().parents[1]


def audit(build):
    unpacked = build / "release/win-unpacked"
    runtime = unpacked / "resources/runtime"
    listing = subprocess.check_output(
        [
            "node",
            str(REPO / "companion/launcher/node_modules/@electron/asar/bin/asar.js"),
            "list",
            str(unpacked / "resources/app.asar"),
        ],
        text=True,
    ).splitlines()
    names = {name.replace("\\", "/").lstrip("/") for name in listing}
    allowed = {
        "assets",
        "assets/icon.ico",
        "assets/items",
        "assets/items/50.png",
        "assets/items/93.png",
        "main.cjs",
        "quantity.js",
        "updater.cjs",
        "preload.cjs",
        "renderer.js",
        "index.html",
        "style.css",
        "package.json",
    }
    assert names == allowed, sorted(names ^ allowed)
    archive = CArchiveReader(str(runtime / "core/PokeApp.Core.exe"))
    modules = [
        name
        for name in archive.open_embedded_archive("PYZ.pyz").toc
        if name.startswith("app.")
    ]
    assert modules and all(
        name.startswith(
            ("app.launcher", "app.save_parser", "app.domain.pokemon_identity")
        )
        or name == "app.domain"
        for name in modules
    ), modules
    for relative in (
        "core/PokeApp.Core.exe",
        "core/_internal/python314.dll",
        "parser/PokeApp.Parser.exe",
        "parser/hostfxr.dll",
        "parser/coreclr.dll",
        "parser/PKHeX.Core.dll",
        "licenses/parser-corresponding-source.zip",
        "licenses/dotnet-LICENSE.TXT",
        "licenses/dotnet-THIRD-PARTY-NOTICES.TXT",
    ):
        assert (runtime / relative).is_file(), relative
    forbidden = {
        ".env",
        "tests",
        "fixtures",
        "evidence",
        ".git",
        "node_modules",
        "migrations",
        "journal.sqlite3",
        "config.json",
        "tokens.dpapi",
    }
    for entry in unpacked.rglob("*"):
        assert not forbidden.intersection(entry.relative_to(unpacked).parts), entry
        assert entry.suffix.lower() not in {".sav", ".dsv", ".srm", ".map", ".pdb"}, (
            entry
        )
    with zipfile.ZipFile(
        runtime / "licenses/parser-corresponding-source.zip"
    ) as source:
        assert not any(
            "/tests/" in name.lower() or "/fixtures/" in name.lower()
            for name in source.namelist()
        )
        for name in (
            "Program.cs",
            "Inspection.cs",
            "NativeWrite.cs",
            "PokeApp.Parser.csproj",
        ):
            assert (
                source.read("adapter/" + name)
                == (REPO / "companion/parser/PokeApp.Parser" / name).read_bytes()
            ), name
    metadata = json.loads(
        subprocess.check_output(
            [
                "node",
                "-e",
                "process.stdout.write(require(process.argv[1]).extractFile(process.argv[2], 'package.json'))",
                str(REPO / "companion/launcher/node_modules/@electron/asar"),
                str(unpacked / "resources/app.asar"),
            ],
            text=True,
        )
    )
    private = metadata.get("pokeappPrivateCandidate") is True
    installer = (
        build
        / "release"
        / (
            "PokeApp-Launcher-Private-Setup.exe"
            if private
            else "PokeApp-Launcher-Setup.exe"
        )
    )
    result = {
        "status": "PASS",
        # The packaged metadata is authoritative (private builds may override it).
        "version": metadata["version"],
        "updates_configured": bool(
            (metadata.get("pokeappUpdate") or {}).get("publicKey")
        ),
        "private_candidate": private,
        "installer": installer.name,
        "sha256": hashlib.sha256(installer.read_bytes()).hexdigest(),
        "bytes": installer.stat().st_size,
        "asar_files": sorted(names),
        "application_modules": sorted(set(modules)),
        "runtime_file_count": len(list(runtime.rglob("*"))),
        "unsigned": True,
    }
    (build / "package-audit.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--build", type=Path, required=True)
    audit(cli.parse_args().build)
