from __future__ import annotations

LEGACY_POINTS_BY_POSITION = {
    1: 9,
    2: 8,
    3: 7,
    4: 6,
    5: 5,
    6: 6,
    7: 5,
    8: 4,
    9: 3,
    10: 2,
    11: 1,
}

LEGACY_COINS_BY_POSITION = {
    1: 15,
    2: 14,
    3: 12,
    4: 11,
    5: 10,
    6: 11,
    7: 10,
    8: 9,
    9: 8,
    10: 7,
    11: 3,
}

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

FIRST_ROUND_B_POINTS_BY_POSITION = {
    6: 5,
    7: 4,
    8: 3,
    9: 2,
    10: 1,
}

FIRST_ROUND_B_COINS_BY_POSITION = {
    6: 11,
    7: 9,
    8: 8,
    9: 6,
    10: 4,
}


def points_for_league_position(tramo: int, pos: int) -> int:
    tramo_i = int(tramo)
    pos_i = int(pos)
    if tramo_i == 1 and pos_i in FIRST_ROUND_B_POINTS_BY_POSITION:
        return FIRST_ROUND_B_POINTS_BY_POSITION[pos_i]
    if tramo_i <= 2:
        return LEGACY_POINTS_BY_POSITION.get(pos_i, 0)
    return CURRENT_POINTS_BY_POSITION.get(pos_i, 0)


def coins_for_league_position(tramo: int, pos: int) -> int:
    tramo_i = int(tramo)
    pos_i = int(pos)
    if tramo_i == 1 and pos_i in FIRST_ROUND_B_COINS_BY_POSITION:
        return FIRST_ROUND_B_COINS_BY_POSITION[pos_i]
    if tramo_i <= 2:
        return LEGACY_COINS_BY_POSITION.get(pos_i, 0)
    return CURRENT_COINS_BY_POSITION.get(pos_i, 0)
