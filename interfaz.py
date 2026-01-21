from __future__ import annotations

from app.interfaz.auth import login_gate
from app.interfaz.badges import coins_from_badges
from app.interfaz.pages import page_copa, page_entrenadores, page_inicio, page_tabla
from app.interfaz.sidebar import render_sidebar
from app.interfaz.theme import apply_css, apply_section_theme, render_poke_separator

__all__ = [
    "apply_css",
    "apply_section_theme",
    "coins_from_badges",
    "login_gate",
    "page_copa",
    "page_entrenadores",
    "page_inicio",
    "page_tabla",
    "render_poke_separator",
    "render_sidebar",
]
