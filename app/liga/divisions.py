from __future__ import annotations


def division_a_size_for_count(player_count: int, round_no: int | None = None) -> int:
    _ = round_no
    return min(5, max(0, int(player_count or 0)))


def movement_count_for_divisions(
    a_size: int,
    b_size: int,
    round_no: int | None = None,
) -> int:
    _ = round_no
    if a_size <= 0 or b_size <= 0:
        return 0
    return min(3, int(a_size), int(b_size))


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
