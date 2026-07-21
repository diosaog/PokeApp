from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path
import unicodedata

from dexdata import type_color
from i18n import translate_type_es


_TYPE_ALIASES = {
    "normal": "Normal",
    "no": "Normal",
    "nor": "Normal",
    "fuego": "Fire",
    "fu": "Fire",
    "fire": "Fire",
    "agua": "Water",
    "ag": "Water",
    "water": "Water",
    "electrico": "Electric",
    "el": "Electric",
    "electric": "Electric",
    "planta": "Grass",
    "pl": "Grass",
    "grass": "Grass",
    "hielo": "Ice",
    "hi": "Ice",
    "ice": "Ice",
    "lucha": "Fighting",
    "lu": "Fighting",
    "fighting": "Fighting",
    "veneno": "Poison",
    "ve": "Poison",
    "poison": "Poison",
    "tierra": "Ground",
    "ti": "Ground",
    "ground": "Ground",
    "volador": "Flying",
    "vo": "Flying",
    "flying": "Flying",
    "psiquico": "Psychic",
    "ps": "Psychic",
    "psychic": "Psychic",
    "bicho": "Bug",
    "bi": "Bug",
    "bug": "Bug",
    "roca": "Rock",
    "ro": "Rock",
    "rock": "Rock",
    "fantasma": "Ghost",
    "fa": "Ghost",
    "ghost": "Ghost",
    "dragon": "Dragon",
    "dr": "Dragon",
    "siniestro": "Dark",
    "si": "Dark",
    "dark": "Dark",
    "acero": "Steel",
    "ac": "Steel",
    "steel": "Steel",
    "hada": "Fairy",
    "ha": "Fairy",
    "fairy": "Fairy",
}

_TYPE_ASSET_SLUGS = {
    "Normal": "normal",
    "Fire": "fire",
    "Water": "water",
    "Electric": "electric",
    "Grass": "grass",
    "Ice": "ice",
    "Fighting": "fighting",
    "Poison": "poison",
    "Ground": "ground",
    "Flying": "flying",
    "Psychic": "psychic",
    "Bug": "bug",
    "Rock": "rock",
    "Ghost": "ghost",
    "Dragon": "dragon",
    "Dark": "dark",
    "Steel": "steel",
    "Fairy": "fairy",
}

_ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "types"


def _normalize_type(type_name: str | None) -> str:
    raw = str(type_name or "Normal").strip()
    if not raw:
        return "Normal"
    key = unicodedata.normalize("NFD", raw.lower())
    key = "".join(ch for ch in key if unicodedata.category(ch) != "Mn")
    return _TYPE_ALIASES.get(key, raw.title())


def _slug(type_name: str) -> str:
    return _TYPE_ASSET_SLUGS.get(type_name, type_name.lower().replace(" ", "-"))


def _text_color(hex_color: str) -> str:
    try:
        if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
            return "#ffffff"
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        lum = (r * 299 + g * 587 + b * 114) / 1000
        return "#182039" if lum > 150 else "#ffffff"
    except Exception:
        return "#ffffff"


@lru_cache(maxsize=64)
def _asset_data_uri(slug: str, full: bool) -> str:
    suffix = "full.png" if full else "icon.svg"
    path = _ASSET_DIR / f"{slug}-{suffix}"
    if not path.exists():
        return ""
    mime = "image/png" if full else "image/svg+xml"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def type_icon_html(
    type_name: str | None,
    *,
    label: bool = False,
    compact: bool = False,
    class_name: str = "",
) -> str:
    resolved = _normalize_type(type_name)
    slug = _slug(resolved)
    color = type_color(resolved)
    fg = _text_color(color)
    label_es = translate_type_es(resolved)
    full = bool(label)
    asset_src = _asset_data_uri(slug, full)
    classes = [
        "poke-type-chip",
        "uses-asset" if asset_src else "uses-fallback",
        "asset-full" if full else "asset-icon",
        f"poke-type-{slug}",
        "is-compact" if compact else "",
        "has-label" if label else "",
        class_name,
    ]
    class_attr = " ".join(part for part in classes if part)
    if asset_src:
        img_class = "poke-type-full-img" if full else "poke-type-icon-img"
        content = (
            f"<img class='{img_class}' src='{asset_src}' "
            f"alt='{escape(label_es)}' loading='lazy'/>"
        )
    else:
        fallback_text = label_es.upper() if label else label_es[:2].upper()
        content = f"<span class='poke-type-fallback'>{escape(fallback_text)}</span>"
    return (
        f"<span class='{class_attr}' title='{escape(label_es)}' "
        f"style='--type-color:{color};--type-fg:{fg}'>"
        f"{content}"
        "</span>"
    )


def type_icons_html(
    types: list[str] | tuple[str, ...] | None,
    *,
    label: bool = False,
    compact: bool = False,
    class_name: str = "",
) -> str:
    return "".join(
        type_icon_html(t, label=label, compact=compact, class_name=class_name)
        for t in list(types or [])[:2]
    )
