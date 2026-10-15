"""Reproduce Phase17 static assets/reference data from pinned upstream commits.

No runtime external requests; never reads a save or connects to the application DB.
"""

import csv
import hashlib
import io
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/visuals/v1"
SPRITES = "ba403973fdf9d0ac59175813861e6a1f8ed5020c"
DATA = "81d20919845b6a445969b9265aab5cec6b04cece"
SHOWDOWN = "8d8d474e677e5a524f6564f2f208111d70cc3a4a"
RAW = "https://raw.githubusercontent.com"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    retained = (
        json.loads((OUT / "manifest.json").read_text())["files"]
        if "--resume" in sys.argv and (OUT / "manifest.json").exists()
        else {}
    )
    with httpx.Client(timeout=60, limits=httpx.Limits(max_connections=12)) as client:

        def get(url):
            response = client.get(url)
            response.raise_for_status()
            return response.content

        def rows(name):
            return list(
                csv.DictReader(
                    io.StringIO(
                        get(
                            f"{RAW}/PokeAPI/pokeapi/{DATA}/data/v2/csv/{name}.csv"
                        ).decode("utf-8")
                    )
                )
            )

        jobs = []
        for i in range(1, 722):
            generation = "generation-v/black-white" if i <= 649 else "generation-vi/x-y"
            jobs.append(
                (
                    f"pokemon/{i}.png",
                    f"{RAW}/PokeAPI/sprites/{SPRITES}/sprites/pokemon/versions/{generation}/{i}.png",
                )
            )
        items = {r["id"]: r["identifier"] for r in rows("items")}
        item_map = {
            r["game_index"]: items[r["item_id"]]
            for r in rows("item_game_indices")
            if r["generation_id"] == "6" and int(r["game_index"]) <= 717
        }
        for i, slug in item_map.items():
            jobs.append(
                (
                    f"items/{i}.png",
                    f"{RAW}/PokeAPI/sprites/{SPRITES}/sprites/items/{slug}.png",
                )
            )
        for category in ["Physical", "Special", "Status"]:
            jobs.append(
                (
                    f"categories/{category}.png",
                    f"{RAW}/smogon/sprites/{SHOWDOWN}/src/_uncategorized/canonical/ui/categories/gen6/{category}.png",
                )
            )
        jobs += [
            (
                "POKEAPI-SPRITES-LICENCE.txt",
                f"{RAW}/PokeAPI/sprites/{SPRITES}/LICENCE.txt",
            ),
            ("POKEAPI-DATA-LICENSE.txt", f"{RAW}/PokeAPI/pokeapi/{DATA}/LICENSE.md"),
            ("SHOWDOWN-README.md", f"{RAW}/smogon/sprites/{SHOWDOWN}/README.md"),
        ]

        def download(job):
            name, url = job
            path = OUT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if retained.get(name, {}).get("unavailable"):
                return name, retained[name]
            try:
                content = (
                    path.read_bytes()
                    if "--resume" in sys.argv and path.exists()
                    else get(url)
                )
            except httpx.HTTPStatusError as error:
                if name.startswith("items/") and error.response.status_code == 404:
                    return name, {"url": url, "unavailable": True}
                raise
            if name.endswith(".png") and not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError(f"Not a PNG: {name}")
            path.write_bytes(content)
            return name, {
                "url": url,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }

        manifest = dict(ThreadPoolExecutor(max_workers=10).map(download, jobs))
        # Exact X/Y reference, never claimed as the current team's game mechanics.
        moves = {r["id"]: r for r in rows("moves") if int(r["id"]) <= 617}
        for change in sorted(
            rows("move_changelog"),
            key=lambda r: int(r["changed_in_version_group_id"]),
            reverse=True,
        ):
            if (
                change["move_id"] in moves
                and int(change["changed_in_version_group_id"]) > 15
            ):
                for field in ["type_id", "power", "accuracy", "pp"]:
                    if change[field] != "":
                        moves[change["move_id"]][field] = change[field]
        descriptions = {
            r["move_id"]: " ".join(r["flavor_text"].split())
            for r in rows("move_flavor_text")
            if r["version_group_id"] == "15" and r["language_id"] == "7"
        }
        reference = {}
        types = {
            1: "Normal",
            2: "Fighting",
            3: "Flying",
            4: "Poison",
            5: "Ground",
            6: "Rock",
            7: "Bug",
            8: "Ghost",
            9: "Steel",
            10: "Fire",
            11: "Water",
            12: "Grass",
            13: "Electric",
            14: "Psychic",
            15: "Ice",
            16: "Dragon",
            17: "Dark",
            18: "Fairy",
        }
        for i, move in moves.items():
            reference[i] = {
                "type": types[int(move["type_id"])],
                "category": {"1": "Status", "2": "Physical", "3": "Special"}[
                    move["damage_class_id"]
                ],
                "power": int(move["power"]) if move["power"] else None,
                "accuracy": int(move["accuracy"]) if move["accuracy"] else None,
                "description": descriptions.get(i),
            }
        (OUT / "moves-xy.json").write_text(
            json.dumps(reference, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    # Reuse existing project art with its original names/notices. No identity guesses.
    for folder, pattern in [
        ("trainers", "*.png"),
        ("shop", "*.*"),
        ("medallas", "*.png"),
        ("types", "*-icon.svg"),
    ]:
        (OUT / folder).mkdir(exist_ok=True)
        for path in (ROOT / "assets" / folder).glob(pattern):
            target = OUT / folder / path.name
            if path.suffix.lower() == ".png":
                with Image.open(path) as image:
                    image.thumbnail(
                        (320, 400) if folder == "trainers" else (96, 96),
                        Image.Resampling.LANCZOS,
                    )
                    image.save(target, optimize=True)
            else:
                shutil.copyfile(path, target)
            manifest[f"{folder}/{path.name}"] = {
                "source": str(path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "bytes": target.stat().st_size,
                "transform": "thumbnail only; original preserved",
            }
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "sprites": SPRITES,
                "data": DATA,
                "showdown": SHOWDOWN,
                "files": dict(sorted(manifest.items())),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    available_items = [
        int(i) for i in item_map if not manifest[f"items/{i}.png"].get("unavailable")
    ]
    (ROOT / "web/src/pokemon/visual-items.json").write_text(
        json.dumps(sorted(available_items), separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"Assets: {len(manifest)} files; reference: {len(reference)} moves; {len(descriptions)} exact X/Y Spanish descriptions"
    )


if __name__ == "__main__":
    main()
