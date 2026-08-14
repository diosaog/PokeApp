from __future__ import annotations

from typing import Any


LEAGUE_ADMIN_USER = "anto"


class LeaguePermissionError(PermissionError):
    """Raised when a non-admin tries to mutate official league state."""


def is_league_admin(user: Any) -> bool:
    return str(user or "").strip().casefold() == LEAGUE_ADMIN_USER


def require_league_admin(user: Any) -> None:
    if not is_league_admin(user):
        raise LeaguePermissionError("Solo Anto puede modificar el estado oficial de Liga.")
