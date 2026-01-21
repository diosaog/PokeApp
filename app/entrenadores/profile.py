from __future__ import annotations

from pathlib import Path
from typing import List

PORTRAITS_DIR = Path("assets") / "trainers"


def slug_candidates(name: str) -> List[str]:
    s = (name or "").strip()
    if not s:
        return []
    base = [s, s.lower(), s.capitalize()]
    norm = s.replace(" ", "_")
    base += [norm, norm.lower()]
    norm2 = s.replace(" ", "-")
    base += [norm2, norm2.lower()]
    return list(dict.fromkeys(base))


def find_trainer_image(trainer: str) -> str | None:
    try:
        if not PORTRAITS_DIR.exists():
            return None
        exts = (".png", ".jpg", ".jpeg", ".webp")
        for cand in slug_candidates(trainer):
            for ext in exts:
                p = PORTRAITS_DIR / f"{cand}{ext}"
                if p.exists():
                    return str(p)
        low = {f.name.lower(): str(f) for f in PORTRAITS_DIR.glob("*") if f.suffix.lower() in exts}
        for cand in slug_candidates(trainer):
            for ext in exts:
                key = f"{cand}{ext}".lower()
                if key in low:
                    return low[key]
        return None
    except Exception:
        return None
