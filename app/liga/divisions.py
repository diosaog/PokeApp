from __future__ import annotations

from app.season.config import division_a_size, movement_count


def division_a_size_for_count(player_count: int, round_no: int | None = None) -> int:
    return division_a_size(int(player_count or 0), round_no)


def movement_count_for_divisions(
    a_size: int,
    b_size: int,
    round_no: int | None = None,
) -> int:
    return movement_count(int(a_size), int(b_size), round_no)


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
