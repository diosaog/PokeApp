from __future__ import annotations

CURRENT_POINTS_BY_POSITION = {
    1: 9,
    2: 8,
    3: 7,
    4: 6,
    5: 5,
    6: 5,
    7: 4,
    8: 3,
    9: 2,
    10: 1,
}

CURRENT_COINS_BY_POSITION = {
    1: 15,
    2: 14,
    3: 12,
    4: 11,
    5: 10,
    6: 11,
    7: 9,
    8: 8,
    9: 6,
    10: 4,
}


def points_for_league_position(
    tramo: int,
    pos: int,
    *,
    field_size: int | None = None,
) -> int:
    _ = tramo, field_size
    return CURRENT_POINTS_BY_POSITION.get(int(pos), 0)


def coins_for_league_position(
    tramo: int,
    pos: int,
    *,
    field_size: int | None = None,
) -> int:
    _ = tramo, field_size
    return CURRENT_COINS_BY_POSITION.get(int(pos), 0)
