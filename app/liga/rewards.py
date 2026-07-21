from __future__ import annotations

from app.season.config import (
    DEFAULT_COINS_BY_POSITION,
    DEFAULT_POINTS_BY_POSITION,
    coins_for_position,
    points_for_position,
)

CURRENT_POINTS_BY_POSITION = DEFAULT_POINTS_BY_POSITION
CURRENT_COINS_BY_POSITION = DEFAULT_COINS_BY_POSITION


def points_for_league_position(
    tramo: int,
    pos: int,
    *,
    field_size: int | None = None,
) -> int:
    _ = field_size
    return points_for_position(int(tramo), int(pos))


def coins_for_league_position(
    tramo: int,
    pos: int,
    *,
    field_size: int | None = None,
) -> int:
    _ = field_size
    return coins_for_position(int(tramo), int(pos))
