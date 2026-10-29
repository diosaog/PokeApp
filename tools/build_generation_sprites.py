"""Per-generation Pokémon images, so a save shows the art of its own games.

Gen6 (X/Y, Omega Ruby/Alpha Sapphire): the pinned repository's X/Y renders,
1-721 plus the explicitly mapped forms, copied byte for byte.
Gen7 (Sun/Moon, Ultra Sun/Ultra Moon): the pinned Ultra Sun/Ultra Moon
animations only exist as GIFs; their FIRST frame becomes a static PNG centred
on the same 96x96 canvas. Nothing is drawn or invented: a species or form
without an image of its generation stays absent and the web shows its neutral
placeholder, never another generation's art.

Same pinned commit and manifest as build_product_assets/build_sprite_variants;
no runtime CDN. Run: python -m tools.build_generation_sprites
"""

import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
from PIL import Image

from tools.build_product_assets import OUT, RAW, ROOT, SPRITES
from tools.build_sprite_variants import FORMS

VERSIONS = f"{RAW}/PokeAPI/sprites/{SPRITES}/sprites/pokemon/versions"
SETS = {
    "gen6": (f"{VERSIONS}/generation-vi/x-y", ".png", 721),
    "gen7": (f"{VERSIONS}/generation-vii/ultra-sun-ultra-moon", ".gif", 807),
}
CANVAS = 96


def first_frame(content):
    """Frame 0 of an animation, transparent, centred on a 96x96 canvas."""
    with Image.open(io.BytesIO(content)) as image:
        image.seek(0)
        frame = image.convert("RGBA")
    box = frame.getbbox()
    if box:
        frame = frame.crop(box)
    if max(frame.size) > CANVAS:
        frame.thumbnail((CANVAS, CANVAS), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(
        frame, ((CANVAS - frame.width) // 2, (CANVAS - frame.height) // 2), frame
    )
    out = io.BytesIO()
    canvas.save(out, "PNG", optimize=True)
    return out.getvalue()


def main():
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    available = {}
    with httpx.Client(timeout=60) as client:

        def fetch(job):
            folder, name, number = job
            source, suffix, _ = SETS[folder]
            url = f"{source}/{number}{suffix}"
            relative = f"{folder}/{name}.png"
            target = OUT / relative
            known = manifest["files"].get(relative)
            if target.exists() and known and known["url"] == url:
                content = target.read_bytes()
                assert known["sha256"] == hashlib.sha256(content).hexdigest(), relative
                return folder, name, relative, known
            response = client.get(url)
            if response.status_code == 404:
                return folder, name, None, None  # no image of this generation
            response.raise_for_status()
            raw = response.content
            if suffix == ".gif":
                content = first_frame(raw)
            else:
                content = raw
                with Image.open(io.BytesIO(content)) as image:
                    assert image.format == "PNG" and image.width > 0
                    image.verify()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            entry = {
                "url": url,
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
            if suffix == ".gif":
                entry["source_sha256"] = hashlib.sha256(raw).hexdigest()
                entry["derived"] = "first animation frame, centred on 96x96"
            return folder, name, relative, entry

        jobs = []
        for folder, (_, _, last) in SETS.items():
            jobs += [(folder, str(n), n) for n in range(1, last + 1)]
            jobs += [
                (folder, key.replace(":", "-form-"), asset)
                for key, asset in FORMS.items()
                if int(key.split(":")[0]) <= last
            ]
        with ThreadPoolExecutor(max_workers=12) as pool:
            for folder, name, relative, entry in pool.map(fetch, jobs):
                if relative:
                    manifest["files"][relative] = entry
                    available.setdefault(folder, []).append(name)
    manifest["files"] = dict(sorted(manifest["files"].items()))
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    index = {
        folder: sorted(names, key=lambda n: (len(n), n))
        for folder, names in sorted(available.items())
    }
    (ROOT / "web/src/pokemon/generation-sprites.json").write_text(
        json.dumps(index, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                folder: {
                    "images": len(names),
                    "bytes": sum(
                        manifest["files"][f"{folder}/{n}.png"]["bytes"] for n in names
                    ),
                }
                for folder, names in index.items()
            }
        )
    )


if __name__ == "__main__":
    main()
