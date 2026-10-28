"""Extend the existing pinned local sprite collection, without replacing its art.

Form indices: https://github.com/kwsch/PKHeX/blob/24.11.11/PKHeX.Core/PKM/Util/Conversion/FormConverter.cs
Asset IDs: the existing pinned PokeAPI pokemon.csv, matched by explicit form name.
No saves, runtime CDN, inferred form order or game-rule changes.
"""

import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
from PIL import Image

from tools.build_product_assets import OUT, RAW, ROOT, SPRITES

FORMS = {
    "6:1": 10034,  # Mega X
    "6:2": 10035,  # Mega Y
    "26:1": 10100,  # Alola
    "386:1": 10001,  # Attack
    "386:2": 10002,  # Defense
    "386:3": 10003,  # Speed
    "479:1": 10008,  # Heat
    "479:2": 10009,  # Wash
    "479:3": 10010,  # Frost
    "479:4": 10011,  # Fan
    "479:5": 10012,  # Mow
    "647:1": 10024,  # Resolute
    "718:1": 10181,  # 10%, Aura Break
    "718:2": 10118,  # 10%, Power Construct
    "718:3": 10119,  # 50%, Power Construct
    "718:4": 10120,  # Complete
}


def main():
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    forms = {key: key.replace(":", "-form-") for key in FORMS}
    jobs = [(str(n), n) for n in range(722, 808)]
    jobs += [(forms[key], asset) for key, asset in FORMS.items()]
    with httpx.Client(timeout=45) as client:

        def download(job):
            name, number = job
            relative = f"pokemon/{name}.png"
            url = f"{RAW}/PokeAPI/sprites/{SPRITES}/sprites/pokemon/{number}.png"
            target = OUT / relative
            if target.exists() and relative in manifest["files"]:
                content = target.read_bytes()
                assert manifest["files"][relative]["url"] == url
                assert (
                    manifest["files"][relative]["sha256"]
                    == hashlib.sha256(content).hexdigest()
                )
            else:
                response = client.get(url)
                response.raise_for_status()
                content = response.content
            with Image.open(io.BytesIO(content)) as image:
                assert image.format == "PNG" and image.width > 0
                image.verify()
            target.write_bytes(content)
            return relative, {
                "url": url,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }

        with ThreadPoolExecutor(max_workers=8) as pool:
            added = dict(pool.map(download, jobs))
    manifest["files"].update(added)
    manifest["files"] = dict(sorted(manifest["files"].items()))
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (ROOT / "web/src/pokemon/visual-forms.json").write_text(
        json.dumps(forms, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "verified_assets": len(added),
                "bytes": sum(row["bytes"] for row in added.values()),
            }
        )
    )


if __name__ == "__main__":
    main()
