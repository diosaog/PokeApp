"""Animated 3D battle models for screens that show a Gen6/7 game's own art.

The Gen6/7 stills (X/Y renders; Ultra Sun/Ultra Moon frame 0) cannot be paired
with the Black/White pixel animations of animated/v1, so since 2026-10-29 those
screens were static. Showdown's animations are the same battle-model clips as
the Ultra Sun/Ultra Moon GIFs the Gen7 stills come from (same frames, ~1/3 of
the bytes); X/Y has no animated set upstream. Pinned PokeAPI/sprites mirror,
base forms 1-807, normal and shiny, multi-frame GIFs only, byte for byte.

Correct species: every animation's first frame, centred like the stills, must
match the published Gen7 still of the same number (silhouette and colour);
anything else is left out and that Pokémon stays static.

Run: python -m tools.build_model_animations
"""

import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
from PIL import Image, ImageChops

from tools.build_generation_sprites import first_frame
from tools.build_product_assets import OUT as STILLS
from tools.build_product_assets import RAW, ROOT, SPRITES

OUT = ROOT / "web/public/visuals/animated/v2"
SOURCE = f"{RAW}/PokeAPI/sprites/{SPRITES}/sprites/pokemon/other/showdown"
LAST = 807
# Reviewed by eye on a contact sheet (Gen7 still | frame 0 | middle frame),
# 2026-10-29: the pixel check failed only on pose or scale (wings mid-flap,
# Typhlosion's flames, a smaller Golbat); same species and form.
SAME_SPECIES_OTHER_POSE = {
    12, 41, 42, 53, 83, 112, 114, 123, 130, 134, 150, 157, 166, 190, 196, 198,
    267, 269, 272, 282, 308, 350, 397, 398, 401, 415, 417, 424, 431, 456, 457,
    470, 471, 475, 621, 795,
}  # fmt: skip
# The clip shows another form than form 0, the only form that animates:
# these stay static rather than show a wrong form.
OTHER_FORM = {
    666: "clip shows the Meadow pattern; form 0 is Icy Snow",
    716: "clip shows Active Mode; form 0 is Neutral Mode",
}


def rgba(content):
    with Image.open(io.BytesIO(content)) as image:
        return image.convert("RGBA")


def matches_still(animation, still):
    """Frame 0 vs the published Gen7 still: overlapping silhouettes and close
    colours. Returns (ok, silhouette IoU, mean colour difference)."""
    a, b = rgba(first_frame(animation)), rgba(still)
    ma = a.getchannel("A").point(lambda v: 255 if v > 64 else 0)
    mb = b.getchannel("A").point(lambda v: 255 if v > 64 else 0)
    inter = sum(ImageChops.multiply(ma, mb).point(lambda v: 1 if v else 0).getdata())
    union = sum(ImageChops.lighter(ma, mb).point(lambda v: 1 if v else 0).getdata())
    iou = inter / union if union else 0.0
    both = ImageChops.multiply(ma, mb)
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    pixels = [d for d, m in zip(diff.getdata(), both.getdata(), strict=True) if m]
    colour = sum(sum(p) / 3 for p in pixels) / len(pixels) if pixels else 255.0
    return iou >= 0.6 and colour <= 48, round(iou, 3), round(colour, 1)


def main():
    (OUT / "shiny").mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60) as client:

        def fetch(job):
            variant, number = job
            folder = "shiny/" if variant == "shiny" else ""
            url = f"{SOURCE}/{folder}{number}.gif"
            target = OUT / f"{folder}{number}.gif"
            if number in OTHER_FORM:
                target.unlink(missing_ok=True)
                return variant, number, {"source": url, "unavailable": OTHER_FORM[number]}
            if target.exists():
                content = target.read_bytes()
            else:
                response = client.get(url)
                if response.status_code == 404:
                    return variant, number, {"source": url, "unavailable": "missing"}
                response.raise_for_status()
                content = response.content
            with Image.open(io.BytesIO(content)) as image:
                frames = getattr(image, "n_frames", 1)
                if image.format != "GIF" or frames < 2:
                    return variant, number, {"source": url, "unavailable": "not animated"}
            entry = {
                "source": url,
                "bytes": len(content),
                "frames": frames,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            if variant == "normal":
                still = STILLS / "gen7" / f"{number}.png"
                if not still.exists():
                    return variant, number, {**entry, "unavailable": "no gen7 still to verify"}
                ok, iou, colour = matches_still(content, still.read_bytes())
                entry.update(silhouette_iou=iou, colour_difference=colour)
                if not ok and number in SAME_SPECIES_OTHER_POSE:
                    entry["reviewed"] = "same species and form, other pose or scale"
                elif not ok:
                    return variant, number, {**entry, "unavailable": "does not match the still"}
            target.write_bytes(content)
            return variant, number, entry

        jobs = [(v, n) for v in ("normal", "shiny") for n in range(1, LAST + 1)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(fetch, jobs))
    files = {"normal": {}, "shiny": {}}
    for variant, number, entry in results:
        files[variant][str(number)] = entry
    normal = {int(n) for n, f in files["normal"].items() if "unavailable" not in f}
    # A shiny clip is used only where the normal one passed the species check.
    shiny = {int(n) for n, f in files["shiny"].items() if "unavailable" not in f} & normal
    for number, entry in files["shiny"].items():
        if "unavailable" not in entry and int(number) not in normal:
            (OUT / "shiny" / f"{number}.gif").unlink(missing_ok=True)
            entry["unavailable"] = "normal clip not verified"
    (OUT / "manifest.json").write_text(
        json.dumps({"revision": SPRITES, "files": files}, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "web/src/pokemon/animated-models.json").write_text(
        json.dumps({"normal": sorted(normal), "shiny": sorted(shiny)}) + "\n", encoding="utf-8"
    )
    (OUT / "ATTRIBUTION.md").write_text(
        "# Animated battle models\n\nPinned PokeAPI/sprites " + SPRITES + " mirror of "
        "Pokémon Showdown's animations (`sprites/pokemon/other/showdown`), base forms "
        f"1-{LAST}, normal and shiny.\nPokémon © Nintendo / Creatures / GAME FREAK. "
        "Model assembly: Smogon community.\nSource URLs, hashes and the species check "
        "against the Gen7 stills: manifest.json. Repository license: "
        "../../v1/POKEAPI-SPRITES-LICENCE.txt. No claim of ownership or general asset "
        "license.\nLoaded only for visible Home/trainer-team/detail sprites of a Gen6/7 "
        "game when motion is enabled; everything else stays static.\n",
        encoding="utf-8",
    )
    rejected = {
        v: {n: f["unavailable"] for n, f in files[v].items() if "unavailable" in f}
        for v in files
    }
    print(json.dumps({
        "normal": len(normal),
        "shiny": len(shiny),
        "bytes": sum(f.get("bytes", 0) for v in files.values() for n, f in v.items()
                     if "unavailable" not in f),
        "rejected": rejected,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
