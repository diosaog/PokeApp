from __future__ import annotations

def page_tabla() -> None:
    from app.liga.ui import page_tabla as _page_tabla

    _page_tabla()


def current_points_total(user: str) -> float:
    from app.liga.ranking import current_points_total as _current_points_total

    return _current_points_total(user)

__all__ = ["page_tabla", "current_points_total"]
