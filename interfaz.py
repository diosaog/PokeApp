from __future__ import annotations

from typing import Any


def apply_css(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.theme import apply_css as _apply_css

    return _apply_css(*args, **kwargs)


def apply_section_theme(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.theme import apply_section_theme as _apply_section_theme

    return _apply_section_theme(*args, **kwargs)


def coins_from_badges(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.badges import coins_from_badges as _coins_from_badges

    return _coins_from_badges(*args, **kwargs)


def login_gate(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.auth import login_gate as _login_gate

    return _login_gate(*args, **kwargs)


def page_copa(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.pages import page_copa as _page_copa

    return _page_copa(*args, **kwargs)


def page_entrenadores(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.pages import page_entrenadores as _page_entrenadores

    return _page_entrenadores(*args, **kwargs)


def page_inicio(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.pages import page_inicio as _page_inicio

    return _page_inicio(*args, **kwargs)


def page_tabla(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.pages import page_tabla as _page_tabla

    return _page_tabla(*args, **kwargs)


def render_poke_separator(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.theme import render_poke_separator as _render_poke_separator

    return _render_poke_separator(*args, **kwargs)


def render_sidebar(*args: Any, **kwargs: Any) -> Any:
    from app.interfaz.sidebar import render_sidebar as _render_sidebar

    return _render_sidebar(*args, **kwargs)

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
