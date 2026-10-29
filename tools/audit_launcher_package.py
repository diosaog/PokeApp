"""Fail closed on unexpected application payloads; runtime and release manifest."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from prepare_launcher_core import required_domain_modules
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
        "assets/fonts",
        "assets/fonts/rubik-latin-wght.woff2",
        "assets/fonts/OFL.txt",
        "main.cjs",
        "quantity.js",
        "updater.cjs",
        "webview.cjs",
        "confirmations.cjs",
        "core-supervisor.cjs",
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
    sources = [
        path for group in ("launcher", "save_parser") for path in (REPO / "app" / group).glob("*.py")
    ]
    domain = set(required_domain_modules(sources))
    assert modules and all(
        name.startswith(("app.launcher", "app.save_parser"))
        or name in domain
        or name == "app.domain"
        for name in modules
    ), modules
    # Every desktop module is really inside: a lazily imported one that the
    # analysis missed fails here, not in the trainer's «Objetos ∞».
    expected = {
        f"app.{path.parent.name}.{path.stem}"
        for path in sources
        if path.stem != "__init__" and path.stem != "__main__"
    } | domain
    assert expected <= set(modules), sorted(expected - set(modules))
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
    preview = metadata.get("pokeappWebPreview")
    variant = metadata.get("pokeappVariant")
    assert variant in (None, "updatetest"), variant
    assert variant is None or private, "update rehearsal in a public build"
    update = metadata.get("pokeappUpdate") or {}
    for channel, feed in (update.get("feed") or {}).items():
        # Public feeds are HTTPS; loopback rehearsal feeds exist only in private.
        assert (
            feed is None
            or feed.startswith("https://")
            or (private and feed.startswith("http://127.0.0.1:"))
        ), (channel, feed)
    assert "PRIVATE KEY" not in json.dumps(update), "private key embedded"
    # A web preview origin is legal only in a private candidate, and only the one.
    assert preview in (None, "http://127.0.0.1:4173"), preview
    assert preview is None or private, "web preview in a public build"
    installer = (
        build
        / "release"
        / (
            "PokeApp-Launcher-UpdateTest-Setup.exe"
            if variant
            else "PokeApp-Launcher-Private-Setup.exe"
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
        "variant": variant,
        "update_feed": update.get("feed") or {},
        "web_origin": preview or "https://pokeapp-web.pokeapp-v2.workers.dev",
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
