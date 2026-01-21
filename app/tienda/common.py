from __future__ import annotations

import unicodedata
from pathlib import Path

from app.common import COIN


def _pokeapi_item_png(slug: str) -> str:
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"


SHOP_DIR = Path("assets") / "shop"


def _shop_asset(slug: str) -> str | None:
    try:
        if not SHOP_DIR.exists():
            return None
        s = (slug or "").strip()
        if not s:
            return None
        candidates = [s, s.replace(" ", "-"), s.replace(" ", "_")]
        for base in candidates:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                p = SHOP_DIR / f"{base}{ext}"
                if p.exists():
                    return str(p)
    except Exception:
        return None
    return None


def _fix_text(s: str) -> str:
    if not s:
        return ""
    t = str(s)
    try:
        alt = t.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        if alt:
            t = alt
    except Exception:
        pass
    replacements = {
        "Pokemon": "Pokemon",
        "Catalogo": "Catalogo",
        "diseno": "diseno",
        "descripcion": "descripcion",
        "Restauracion": "Restauracion",
        "Curacion": "Curacion",
        "congelacion": "congelacion",
        "confusion": "confusion",
        "Fosil": "Fosil",
        "Electrico": "Electrico",
        "critico": "critico",
    }
    for a, b in replacements.items():
        t = t.replace(a, b)
    for bad, good in {
        "\u00C3\u00B1": "n",
        "\u00C3\u00A1": "a",
        "\u00C3\u00A9": "e",
        "\u00C3\u00AD": "i",
        "\u00C3\u00B3": "o",
        "\u00C3\u00BA": "u",
        "\u00C3\u0081": "A",
        "\u00C3\u0089": "E",
        "\u00C3\u008D": "I",
        "\u00C3\u0093": "O",
        "\u00C3\u009A": "U",
    }.items():
        t = t.replace(bad, good)
    return t


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def _eq_item(a: str, b: str) -> bool:
    return _norm(a) == _norm(b)


def _is_usable_item(name: str) -> bool:
    targets = ("Revivir Pokemon", "Robar Pokemon", "Blindar Pokemon", "Comodin de Blindaje por Robo")
    return any(_eq_item(name, t) for t in targets)
