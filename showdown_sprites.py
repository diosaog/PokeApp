"""
Utilidades para mostrar sprites de Pokémon Showdown (estáticos o animados)
- Convierte especie/forma  slug de Showdown.
- Genera URLs para PNG (gen5) o GIF (ani / ani-shiny).
- Maneja casos especiales (Mr. Mime, Ho-Oh, Type: Null, etc.) y formas comunes (Rotom, Giratina, Shaymin, Wormadam, Shellos/Gastrodon, Deoxys...).
- Plug-and-play con Streamlit.

Uso rápido:
    from showdown_sprites import showdown_sprite_url
    st.image(showdown_sprite_url(species_name="Turtwig", dex_id=387))

Sugerencia:
- Si tienes `form_index` de PKHeX, pásalo. Si no, `form_name` como texto.
- Si quieres animados por defecto: prefer_animated=True.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

from functools import lru_cache
# =========================
# 1) Normalización de nombres
# =========================

# Reparaciones puntuales de nombres a slug base
SPECIAL_BASE = {
    # Puntuación
    "mr. mime": "mrmime",
    "mr mime": "mrmime",
    "mr. rime": "mrrime",
    "mr rime": "mrrime",
    "ho-oh": "hooh",
    "farfetch'd": "farfetchd",
    "sirfetch'd": "sirfetchd",
    "jangmo-o": "jangmoo",
    "hakamo-o": "hakamoo",
    "kommo-o": "kommoo",
    "type: null": "typenull",
    "tapukoko": "tapukoko",  # ejemplo de ya-normalizado
}

def _base_slug(species_name: str) -> str:
    s = species_name.strip().lower()
    if s in SPECIAL_BASE:
        return SPECIAL_BASE[s]
    # quitar todo menos a-z0-9
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

# =========================
# 2) Formas: tablas y helpers
# =========================
# Nota: muchos proyectos sólo usan estas. Amplía si tu randomizer trae más variantes.

# Femeninos con sprite distinto y sufijo -f (cuando el juego lo usa así en Showdown)
FEMALE_DIFF = {
    "meowstic", "unfezant", "frillish", "jellicent", "indeedee",
    # Añade si te topas con más
}

# Mapas de forma por especie (index  sufijo Showdown)
ROTOM_FORMS = {
    1: "heat", 2: "wash", 3: "frost", 4: "fan", 5: "mow",
}
WORMADAM_FORMS = {1: "sandy", 2: "trash"}
BURMY_FORMS = {1: "sandy", 2: "trash"}
SHELLOS_FORMS = {1: "east"}        # 0: west (base), 1: east
GASTRODON_FORMS = {1: "east"}
GIRATINA_FORMS = {1: "origin"}
SHAYMIN_FORMS = {1: "sky"}
DEOXYS_FORMS = {1: "attack", 2: "defense", 3: "speed"}

# Aliases de texto  forma estandarizada
FORM_ALIASES = {
    "alola": "alola", "alolan": "alola",
    "galar": "galar", "galarian": "galar",
    "hisui": "hisui", "hisuian": "hisui",
    "paldea": "paldea", "paldean": "paldea",
    "mega": "mega", "megax": "megax", "megay": "megay",
    "gmax": "gmax", "gigantamax": "gmax",
    "origin": "origin", "sky": "sky",
    "east": "east", "sandy": "sandy", "trash": "trash",
    "heat": "heat", "wash": "wash", "frost": "frost", "fan": "fan", "mow": "mow",
}

# =========================
# 3) API pública
# =========================
@dataclass
class MonLite:
    species_name: str
    dex_id: Optional[int] = None  # por si prefieres usarlo en otro lado
    form_index: Optional[int] = None
    form_name: Optional[str] = None
    is_shiny: bool = False
    gender: Optional[str] = None  # "M", "F" o None
@lru_cache(maxsize=2048)
def showdown_id(
    species_name: str,
    *,
    form_index: Optional[int] = None,
    form_name: Optional[str] = None,
    gender: Optional[str] = None,
) -> str:
    """Devuelve el slug Showdown: 'giratina-origin', 'rotom-heat', 'mrmime', etc.
    Prioriza form_index si viene; si no, intenta parsear form_name de texto.
    """
    base = _base_slug(species_name)

    # --- Formas por índice (cuando provienen de PKHeX) ---
    if base == "rotom" and (form_index or 0) in ROTOM_FORMS:
        return f"rotom-{ROTOM_FORMS[form_index]}"
    if base == "wormadam" and (form_index or 0) in WORMADAM_FORMS:
        return f"wormadam-{WORMADAM_FORMS[form_index]}"
    if base == "burmy" and (form_index or 0) in BURMY_FORMS:
        return f"burmy-{BURMY_FORMS[form_index]}"
    if base == "shellos" and (form_index or 0) in SHELLOS_FORMS:
        return f"shellos-{SHELLOS_FORMS[form_index]}"
    if base == "gastrodon" and (form_index or 0) in GASTRODON_FORMS:
        return f"gastrodon-{GASTRODON_FORMS[form_index]}"
    if base == "giratina" and (form_index or 0) in GIRATINA_FORMS:
        return f"giratina-{GIRATINA_FORMS[form_index]}"
    if base == "shaymin" and (form_index or 0) in SHAYMIN_FORMS:
        return f"shaymin-{SHAYMIN_FORMS[form_index]}"
    if base == "deoxys" and (form_index or 0) in DEOXYS_FORMS:
        return f"deoxys-{DEOXYS_FORMS[form_index]}"

    # --- Formas por nombre de texto (regional, mega, gmax, etc.) ---
    if form_name:
        f = form_name.strip().lower()
        f = FORM_ALIASES.get(f, f)
        f = re.sub(r"[^a-z0-9]", "", f)
        # megas y gmax pegan sufijo directo
        if f in {"mega", "megax", "megay", "gmax", "origin", "sky", "east",
                 "sandy", "trash", "heat", "wash", "frost", "fan", "mow",
                 "alola", "galar", "hisui", "paldea"}:
            return f"{base}-{f}"

    # --- Variante femenina cuando Showdown usa -f ---
    if gender == "F" and base in FEMALE_DIFF:
        return f"{base}-f"

    # Por defecto, base
    return base


def url_showdown_static(name_id: str) -> str:
    """PNG estático (gen5)"""
    return f"https://play.pokemonshowdown.com/sprites/gen5/{name_id}.png"


def url_showdown_ani(name_id: str, shiny: bool = False) -> str:
    """GIF animado (ani / ani-shiny)"""
    folder = "ani-shiny" if shiny else "ani"
    return f"https://play.pokemonshowdown.com/sprites/{folder}/{name_id}.gif"
@lru_cache(maxsize=4096)
def showdown_sprite_url(
    *,
    species_name: str,
    dex_id: Optional[int] = None,
    form_index: Optional[int] = None,
    form_name: Optional[str] = None,
    is_shiny: bool = False,
    gender: Optional[str] = None,
    prefer_animated: bool = True,
) -> str:
    """Devuelve la URL del sprite (elige animado o estático)."""
    sid = showdown_id(species_name, form_index=form_index, form_name=form_name, gender=gender)
    if prefer_animated:
        return url_showdown_ani(sid, shiny=is_shiny)
    return url_showdown_static(sid)

# =========================
# 4) Integración con Streamlit  ejemplo (opcional)
# =========================
# Pega este bloque donde pintas equipos/cajas.
#
# import streamlit as st
# from showdown_sprites import showdown_sprite_url
#
# def card_mon(mon):
#     # mon: objeto con .species_name, .form_index, .form_name, .is_shiny, .gender
#     img = showdown_sprite_url(
#         species_name=mon.species_name,
#         form_index=getattr(mon, "form_index", None),
#         form_name=getattr(mon, "form_name", None),
#         is_shiny=getattr(mon, "is_shiny", False),
#         gender=getattr(mon, "gender", None),
#         prefer_animated=True,
#     )
#     st.image(img, width=96)
#     st.caption(f"{mon.species_name} Lv.{getattr(mon, 'level', '?')}")
#
# def grid_box(mons):
#     cols = st.columns(6)
#     for i, mon in enumerate(mons):
#         with cols[i % 6]:
#             card_mon(mon)
#
# # Ejemplo de uso:
# # grid_box(equipo_o_caja)





