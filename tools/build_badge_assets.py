"""Small reproducible art-only extension; no gameplay, database or save access."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
REV = "ba403973fdf9d0ac59175813861e6a1f8ed5020c"
OUT = ROOT / "web/public/visuals/badges/v1"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30) as client:
        def download(number):
            url = f"https://raw.githubusercontent.com/PokeAPI/sprites/{REV}/sprites/badges/{number}.png"
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Expected PNG")
            (OUT / f"{number}.png").write_bytes(content)
            return str(number), {"source": url, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
        files = dict(ThreadPoolExecutor(max_workers=8).map(download, range(1, 51)))
    (OUT / "manifest.json").write_text(json.dumps({"revision": REV, "files": files}, indent=2) + "\n", encoding="utf-8")
    # Tiny eager type lookup; full descriptions remain interaction-only.
    moves = json.loads((ROOT / "web/public/visuals/v1/moves-xy.json").read_text(encoding="utf-8"))
    (ROOT / "web/src/pokemon/move-types.json").write_text(json.dumps({k: v["type"] for k, v in moves.items()}, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(files)} badges; {sum(f['bytes'] for f in files.values())} bytes")


if __name__ == "__main__":
    main()
