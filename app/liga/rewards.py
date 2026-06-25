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

EIGHT_PLAYER_POINTS_BY_POSITION = {
    1: 7,
    2: 6,
    3: 5,
    4: 4,
    5: 4,
    6: 3,
    7: 2,
    8: 1,
}

EIGHT_PLAYER_COINS_BY_POSITION = {
    1: 15,
    2: 13,
    3: 11,
    4: 10,
    5: 11,
    6: 9,
    7: 7,
    8: 5,
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


def field_size_for_round_results(results: dict, tramo: int) -> int:
    round_no = int(tramo)
    positions: list[int] = []
    for round_map in (results or {}).values():
        if not isinstance(round_map, dict):
            continue
        raw_pos = round_map.get(round_no, round_map.get(str(round_no)))
        try:
            positions.append(int(raw_pos))
        except Exception:
            continue
    return max(positions) if positions else 0


def points_for_league_position(
    tramo: int,
    pos: int,
    *,
    field_size: int | None = None,
) -> int:
    tramo_i = int(tramo)
    pos_i = int(pos)
    field_size_i = int(field_size or 0)
    if tramo_i >= 4 and field_size_i and field_size_i <= 8:
        return EIGHT_PLAYER_POINTS_BY_POSITION.get(pos_i, 0)
    if tramo_i == 1 and pos_i in FIRST_ROUND_B_POINTS_BY_POSITION:
        return FIRST_ROUND_B_POINTS_BY_POSITION[pos_i]
    if tramo_i <= 2:
        return LEGACY_POINTS_BY_POSITION.get(pos_i, 0)
    return CURRENT_POINTS_BY_POSITION.get(pos_i, 0)


def coins_for_league_position(
    tramo: int,
    pos: int,
    *,
    field_size: int | None = None,
) -> int:
    tramo_i = int(tramo)
    pos_i = int(pos)
    field_size_i = int(field_size or 0)
    if tramo_i >= 4 and field_size_i and field_size_i <= 8:
        return EIGHT_PLAYER_COINS_BY_POSITION.get(pos_i, 0)
    if tramo_i == 1 and pos_i in FIRST_ROUND_B_COINS_BY_POSITION:
        return FIRST_ROUND_B_COINS_BY_POSITION[pos_i]
    if tramo_i <= 2:
        return LEGACY_COINS_BY_POSITION.get(pos_i, 0)
    return CURRENT_COINS_BY_POSITION.get(pos_i, 0)
