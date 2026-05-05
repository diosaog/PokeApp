from __future__ import annotations

def page_juicios() -> None:
    from app.juicios.ui import page_juicios as _page_juicios

    _page_juicios()

__all__ = ["page_juicios"]
