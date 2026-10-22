"""Assemble distribution notices and the covered parser source, never repo-wide."""

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile
from importlib import metadata
from pathlib import Path

UPSTREAM = "b60c6e5f1427263260061d3f8c5540b924063572"
REPO = Path(__file__).resolve().parents[1]


def prepare(stage, build):
    notices = stage / "licenses"
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "companion/parser/third-party/PKHeX-LICENSE.md", notices)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("Python distribution license missing")
    shutil.copy2(python_license, notices / "Python-LICENSE.txt")
    packages = Path(
        os.environ.get("NUGET_PACKAGES", str(Path.home() / ".nuget/packages"))
    )
    dotnet = packages / "microsoft.netcore.app.runtime.win-x64/8.0.29"
    for name in ("LICENSE.TXT", "THIRD-PARTY-NOTICES.TXT"):
        shutil.copy2(dotnet / name, notices / ("dotnet-" + name))
    for dist in metadata.distributions():
        for entry in dist.files or []:
            if ".dist-info/" in str(entry).replace("\\", "/") and any(
                word in entry.name.lower() for word in ("license", "copying", "notice")
            ):
                src = Path(dist.locate_file(entry))
                if src.is_file():
                    target = notices / dist.metadata["Name"] / entry.name
                    target.parent.mkdir(exist_ok=True)
                    shutil.copy2(src, target)
    archive = build / "pkhex-source.zip"
    if not archive.exists():
        urllib.request.urlretrieve(
            f"https://codeload.github.com/kwsch/PKHeX/zip/{UPSTREAM}", archive
        )
    if (
        hashlib.sha256(archive.read_bytes()).hexdigest()
        != "e469c98a6e50f20e3ca1f3c9875caea3ebffc214b0ecbd9abf3cb504b1f5086e"
    ):
        raise RuntimeError("Pinned PKHeX source archive hash mismatch")
    with (
        zipfile.ZipFile(archive) as upstream,
        zipfile.ZipFile(
            notices / "parser-corresponding-source.zip", "w", zipfile.ZIP_DEFLATED
        ) as source,
    ):
        for entry in upstream.infolist():
            relative = Path(*Path(entry.filename).parts[1:])
            if not entry.is_dir() and (
                relative.parts[0] == "PKHeX.Core"
                or (
                    len(relative.parts) == 1
                    and relative.name
                    in (
                        "LICENSE",
                        "Directory.Build.props",
                        "Directory.Build.targets",
                        "NuGet.Config",
                        "global.json",
                    )
                )
            ):
                source.writestr(f"upstream/{relative.as_posix()}", upstream.read(entry))
        for filename in (
            "Program.cs",
            "Inspection.cs",
            "NativeWrite.cs",
            "PokeApp.Parser.csproj",
        ):
            source.write(
                REPO / "companion/parser/PokeApp.Parser" / filename,
                f"adapter/{filename}",
            )
        source.write(
            REPO / "companion/launcher/parser-win-x64.lock.json",
            "adapter/packages.lock.json",
        )
        source.writestr(
            "BUILD.txt",
            (
                "PokeApp native parser/writer adapter, distributed under GPL-3.0-or-later.\n"
                "No upstream modifications. See upstream/LICENSE.\n"
                "Build the adapter with .NET SDK 9.0.318:\n"
                "dotnet publish adapter/PokeApp.Parser.csproj -c Release -r win-x64 "
                "--self-contained true -p:RuntimeFrameworkVersion=8.0.29 -p:RestoreLockedMode=true\n"
                f"Upstream source: https://github.com/kwsch/PKHeX/tree/{UPSTREAM}/PKHeX.Core\n"
                "The original pinned NuGet PKHeX.Core 24.11.11 is used; package content hash is in the lock.\n"
                "NuGet metadata identifies 241112052953, not a Git SHA. No bit-identical source-to-package claim.\n"
                "The source archive includes the upstream Core project and its data/build inputs.\n"
            ),
        )
    (notices / "NOTICE.txt").write_text(
        "PokeApp Launcher — third-party notices\n"
        "PKHeX.Core 24.11.11: copyright Kaphotics and contributors, GPL-3.0-or-later.\n"
        "The covered parser/writer source and build instructions are included in parser-corresponding-source.zip.\n"
        "No warranty. This notice does not relicense the whole private PokeApp repository.\n"
        "Electron/Chromium license texts are installed beside the Launcher executable.\n"
        "Python, Python package and .NET license texts are in this directory.\n"
        "PyInstaller is a build tool with its bootloader distribution exception.\n"
        f"Upstream source archive SHA-256: {hashlib.sha256(archive.read_bytes()).hexdigest()}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--stage", required=True, type=Path)
    cli.add_argument("--build", required=True, type=Path)
    args = cli.parse_args()
    prepare(args.stage, args.build)
