from __future__ import annotations

from html import escape
import unicodedata

from dexdata import type_color
from i18n import translate_type_es


_TYPE_ALIASES = {
    "normal": "Normal",
    "fuego": "Fire",
    "fire": "Fire",
    "agua": "Water",
    "water": "Water",
    "electrico": "Electric",
    "electric": "Electric",
    "planta": "Grass",
    "grass": "Grass",
    "hielo": "Ice",
    "ice": "Ice",
    "lucha": "Fighting",
    "fighting": "Fighting",
    "veneno": "Poison",
    "poison": "Poison",
    "tierra": "Ground",
    "ground": "Ground",
    "volador": "Flying",
    "flying": "Flying",
    "psiquico": "Psychic",
    "psychic": "Psychic",
    "bicho": "Bug",
    "bug": "Bug",
    "roca": "Rock",
    "rock": "Rock",
    "fantasma": "Ghost",
    "ghost": "Ghost",
    "dragon": "Dragon",
    "siniestro": "Dark",
    "dark": "Dark",
    "acero": "Steel",
    "steel": "Steel",
    "hada": "Fairy",
    "fairy": "Fairy",
}

_TYPE_SVG = {
    "Normal": "<circle cx='12' cy='12' r='6.5'/>",
    "Fire": "<path d='M12 22c-4.2 0-7-3-7-7.2 0-2.7 1.5-5 3.5-7.1-.1 2.4 1.4 3.9 2.5 4.6.2-4.1 2.8-7.5 5.5-10.3-.1 5.3 3.5 7.2 3.5 12.4 0 4.5-3.1 7.6-8 7.6z'/>",
    "Water": "<path d='M12 2.5c3.6 4.3 6.1 7.6 6.1 11.5 0 4.4-2.5 7.3-6.1 7.3S5.9 18.4 5.9 14c0-3.9 2.5-7.2 6.1-11.5z'/>",
    "Electric": "<path d='M14 1.8 5.5 13h5.2L9.2 22.2 18.7 9.8h-5.3L14 1.8z'/>",
    "Grass": "<path d='M20.7 3.1C12.2 3.4 6 7.7 5.4 14.2c-.3 3.4 1.8 6 5.1 6.3 6.5.5 10.6-5.8 10.2-17.4zM6.2 19.2c3.6-4.5 7.1-7.3 11.2-9.2' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round'/>",
    "Ice": "<path d='M12 2v20M4.9 5.2l14.2 13.6M19.1 5.2 4.9 18.8' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round'/>",
    "Fighting": "<path d='M6 9.5h12v5.4c0 3.7-2.7 6.1-6 6.1s-6-2.4-6-6.1V9.5zM7.2 8.7V5.2c0-1.3.9-2.2 2-2.2s2 .9 2 2.2v3.5M11.2 8.7V4.2c0-1.3.9-2.2 2-2.2s2 .9 2 2.2v4.5M15.2 8.7V5.5c0-1.2.8-2 1.9-2s1.9.8 1.9 2v5.7'/>",
    "Poison": "<path d='M12 3.2c4.2 0 7.2 2.6 7.2 6.3 0 2.9-1.7 4.9-4.3 5.8l1.6 4.8H7.5l1.6-4.8c-2.6-.9-4.3-2.9-4.3-5.8 0-3.7 3-6.3 7.2-6.3zM8.7 10.2h.1M15.2 10.2h.1'/>",
    "Ground": "<path d='M2.8 19.5 9.6 5.1l3.6 7.4 2.2-4.2 5.8 11.2H2.8z'/>",
    "Flying": "<path d='M21 5.2C13.5 6 8.5 9.1 5.3 14.8l-2.3 4 4.3-1.7c6.1-2.4 10.6-6.6 13.7-11.9z'/>",
    "Psychic": "<path d='M12 4.2c5.1 0 8.7 4.2 9.7 7.8-1 3.6-4.6 7.8-9.7 7.8S3.3 15.6 2.3 12C3.3 8.4 6.9 4.2 12 4.2zm0 4.2a3.6 3.6 0 1 0 0 7.2 3.6 3.6 0 0 0 0-7.2z'/>",
    "Bug": "<path d='M7 10.5c0-3.2 2.1-5.8 5-5.8s5 2.6 5 5.8v3.4c0 3.3-2.1 5.9-5 5.9s-5-2.6-5-5.9v-3.4zM4.2 8.2 7 10.1M19.8 8.2 17 10.1M4 16.5 7.2 15M20 16.5 16.8 15M9.2 4.4 7.4 2.2M14.8 4.4l1.8-2.2' fill='none' stroke='currentColor' stroke-width='2.4' stroke-linecap='round'/>",
    "Rock": "<path d='M4 8.2 10.4 3h6.2L21 10.5 17.8 21H6.7L3 13.2 4 8.2z'/>",
    "Ghost": "<path d='M5.2 20.8V9.8c0-4.1 2.8-7 6.8-7s6.8 2.9 6.8 7v11l-3.1-1.9-2.5 1.9-2.5-1.9-2.5 1.9-3-1.9zM9.4 10h.1M14.5 10h.1'/>",
    "Dragon": "<path d='M19.8 3.2c-7.9.6-13.2 5-13.2 10.7 0 4.1 3.1 7.1 7.3 7.1 2.2 0 4.1-.8 5.6-2.2-1.6.3-3.5.1-5-.9-2.4-1.5-3.1-4.5-1.8-7 1.2-2.4 3.6-4.6 7.1-7.7z'/>",
    "Dark": "<path d='M18.8 18.5A8.9 8.9 0 0 1 6.2 5.9c2.4-2.4 5.8-3.1 8.8-2.2-3.8 1.1-6.5 4.5-6.5 8.4s2.7 7.3 6.5 8.4c1.4-.4 2.7-1.1 3.8-2z'/>",
    "Steel": "<path d='M12 2.6 21 8v8l-9 5.4L3 16V8l9-5.4zm0 5.3a4.1 4.1 0 1 0 0 8.2 4.1 4.1 0 0 0 0-8.2z'/>",
    "Fairy": "<path d='M12 2.4 14.5 9l6.8 2.5-6.8 2.5-2.5 7.6L9.5 14l-6.8-2.5L9.5 9 12 2.4z'/>",
}


def _normalize_type(type_name: str | None) -> str:
    raw = str(type_name or "Normal").strip()
    if not raw:
        return "Normal"
    key = unicodedata.normalize("NFD", raw.lower())
    key = "".join(ch for ch in key if unicodedata.category(ch) != "Mn")
    return _TYPE_ALIASES.get(key, raw.title())


def _slug(type_name: str) -> str:
    return type_name.lower().replace(" ", "-")


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


def type_icon_html(
    type_name: str | None,
    *,
    label: bool = False,
    compact: bool = False,
    class_name: str = "",
) -> str:
    resolved = _normalize_type(type_name)
    color = type_color(resolved)
    label_es = translate_type_es(resolved)
    classes = [
        "poke-type-chip",
        f"poke-type-{_slug(resolved)}",
        "is-compact" if compact else "",
        "has-label" if label else "",
        class_name,
    ]
    class_attr = " ".join(part for part in classes if part)
    label_html = f"<span class='poke-type-label'>{escape(label_es.upper())}</span>" if label else ""
    svg = _TYPE_SVG.get(resolved, _TYPE_SVG["Normal"])
    return (
        f"<span class='{class_attr}' title='{escape(label_es)}' "
        f"style='--type-color:{color};--type-fg:{_text_color(color)}'>"
        "<span class='poke-type-icon' aria-hidden='true'>"
        f"<svg viewBox='0 0 24 24' focusable='false'>{svg}</svg>"
        "</span>"
        f"{label_html}"
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
