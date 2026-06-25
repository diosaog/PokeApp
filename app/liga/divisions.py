from __future__ import annotations


def uses_eight_player_league_rules(round_no: int | None, player_count: int | None = None) -> bool:
    try:
        if int(round_no or 0) < 4:
            return False
    except Exception:
        return False
    if player_count is None:
        return True
    try:
        return int(player_count or 0) <= 8
    except Exception:
        return False


def division_a_size_for_count(player_count: int, round_no: int | None = None) -> int:
    total = max(0, int(player_count or 0))
    if total <= 0:
        return 0
    if uses_eight_player_league_rules(round_no, total):
        return min(4, total)
    return min(5, total)


def movement_count_for_divisions(
    a_size: int,
    b_size: int,
    round_no: int | None = None,
) -> int:
    if a_size <= 0 or b_size <= 0:
        return 0
    base = 2 if uses_eight_player_league_rules(round_no, a_size + b_size) else 3
    return min(base, a_size, b_size)


def next_divisions_from_rankings(
    rank_a: list[str],
    rank_b: list[str],
    round_no: int | None = None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    movement_count = movement_count_for_divisions(len(rank_a), len(rank_b), round_no)
    stay_a_count = max(len(rank_a) - movement_count, 0)
    up = rank_b[:movement_count]
    down = rank_a[stay_a_count:]
    new_a = rank_a[:stay_a_count] + up
    new_b = down + rank_b[movement_count:]
    return new_a, new_b, up, down
