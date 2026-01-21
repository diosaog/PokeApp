from __future__ import annotations

from app.entrenadores.page import (
    page_entrenadores,
    page_entrenadores_setup,
    page_entrenadores_view,
)
from app.entrenadores.sprites import sprite_url_from_p as _sprite_url_from_p
from app.entrenadores.badges import count_badges as _count_badges
from app.entrenadores.bridge import try_auto_load_bridge as _try_auto_load_bridge
from app.entrenadores.pokepaste import sanitize_mon as _sanitize_mon
from app.liga.coins import coins_from_league

__all__ = [
    "page_entrenadores",
    "page_entrenadores_setup",
    "page_entrenadores_view",
    "_sprite_url_from_p",
    "_count_badges",
    "_try_auto_load_bridge",
    "_sanitize_mon",
    "coins_from_league",
]
