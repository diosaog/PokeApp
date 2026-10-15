"""Pinned real sprites; opt-in team/detail presentation, never a runtime CDN."""
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/visuals/animated/v1"
REV = "ba403973fdf9d0ac59175813861e6a1f8ed5020c"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=45) as client:
        def sprite(number):
            folder = "versions/generation-v/black-white/animated" if number <= 649 else "other/showdown"
            url = f"https://raw.githubusercontent.com/PokeAPI/sprites/{REV}/sprites/pokemon/{folder}/{number}.gif"
            path = OUT / f"{number}.gif"
            if path.exists():
                content = path.read_bytes()
            else:
                response = client.get(url)
                if response.status_code == 404:
                    return str(number), {"source": url, "unavailable": True}
                response.raise_for_status()
                content = response.content
            with Image.open(io.BytesIO(content)) as img:
                if img.format != "GIF" or img.n_frames < 2:
                    return str(number), {"source": url, "unavailable": True}
                frames = img.n_frames
            path.write_bytes(content)
            return str(number), {"source": url, "bytes": len(content), "frames": frames,
                                     "sha256": hashlib.sha256(content).hexdigest()}
        with ThreadPoolExecutor(max_workers=10) as pool:
            files = dict(pool.map(sprite, range(1, 722)))
    (OUT / "manifest.json").write_text(json.dumps({"revision": REV, "files": files}, indent=2)+"\n")
    (ROOT / "web/src/pokemon/animated-sprites.json").write_text(
        json.dumps([int(n) for n, f in files.items() if not f.get("unavailable")])+"\n")
    (OUT / "ATTRIBUTION.md").write_text(
        "# Animated Pokémon assets\n\nPinned PokeAPI/sprites " + REV +
        ". Gen 1–5 use original Black/White animations; Gen 6 uses Showdown models.\n"
        "Pokémon © Nintendo / Creatures / GAME FREAK. Model assembly: Smogon community.\n"
        "Source URLs and hashes: manifest.json. Repository license is retained at "
        "../../v1/POKEAPI-SPRITES-LICENCE.txt. No claim of ownership or general asset license.\n"
        "Loaded only for visible party/team/detail when motion is enabled; boxes stay static.\n",
        encoding="utf-8")
    print(json.dumps({"available": sum(not f.get('unavailable') for f in files.values()),
                         "bytes": sum(f.get('bytes', 0) for f in files.values())}))


if __name__ == "__main__":
    main()
