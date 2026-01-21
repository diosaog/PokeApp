from __future__ import annotations

from app.entrenadores.constants import TEAM_IMG_W
from showdown_sprites import showdown_sprite_url


def url_official_art_by_id(dex_id: int) -> str:
    return (
        "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/"
        f"pokemon/other/official-artwork/{dex_id}.png"
    )


def sprite_url_from_p(p: dict, *, prefer_animated: bool = True) -> str:
    species_name = p.get("species_name") or p.get("species")
    if isinstance(species_name, str) and species_name.startswith("#") and species_name[1:].isdigit():
        species_name = None
    if species_name:
        return showdown_sprite_url(
            species_name=species_name,
            form_index=p.get("form_index"),
            form_name=p.get("form_name"),
            is_shiny=bool(p.get("is_shiny", False)),
            gender=p.get("gender"),
            prefer_animated=prefer_animated,
        )
    dex_id = p.get("dex_id")
    if isinstance(dex_id, int) and dex_id > 0:
        return url_official_art_by_id(dex_id)
    return f"https://via.placeholder.com/{TEAM_IMG_W}?text=PKM"
