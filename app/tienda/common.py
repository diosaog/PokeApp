from __future__ import annotations

import base64
import mimetypes
import unicodedata
from pathlib import Path


def _pokeapi_item_png(slug: str) -> str:
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"


SHOP_DIR = Path("assets") / "shop"
_ASSET_URI_CACHE: dict[tuple[str, float | None], str] = {}


def _shop_asset(slug: str) -> str | None:
    try:
        if not SHOP_DIR.exists():
            return None
        s = (slug or "").strip()
        if not s:
            return None
        candidates = [s, s.replace(" ", "-"), s.replace(" ", "_")]
        for base in candidates:
            for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
                p = SHOP_DIR / f"{base}{ext}"
                if p.exists():
                    return str(p)
    except Exception:
        return None
    return None


def _file_data_uri(path: str) -> str:
    try:
        if not path:
            return ""
        p = Path(path)
        if not p.exists():
            return ""
        try:
            mtime = p.stat().st_mtime
        except Exception:
            mtime = None
        key = (str(p), mtime)
        if key in _ASSET_URI_CACHE:
            return _ASSET_URI_CACHE[key]
        mt = mimetypes.guess_type(str(p))[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        uri = f"data:{mt};base64,{b64}"
        _ASSET_URI_CACHE[key] = uri
        return uri
    except Exception:
        return ""


def _resolve_img_src(src: str) -> str:
    if not src:
        return ""
    try:
        p = Path(src)
        if p.exists():
            uri = _file_data_uri(str(p))
            return uri or src
    except Exception:
        pass
    return src


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
