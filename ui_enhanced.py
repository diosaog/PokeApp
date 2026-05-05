from __future__ import annotations

from typing import Any


def team_grid_ui(*args: Any, **kwargs: Any) -> Any:
    from app.ui.team_grid import team_grid_ui as _team_grid_ui

    return _team_grid_ui(*args, **kwargs)

__all__ = ["team_grid_ui"]
