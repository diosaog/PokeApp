from __future__ import annotations

from app.domain.services.league import calculate_division_movements
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
    count = movement_count_for_divisions(len(rank_a), len(rank_b), round_no)
    movement = calculate_division_movements(rank_a, rank_b, count)
    return (
        list(movement.new_a),
        list(movement.new_b),
        list(movement.promoted),
        list(movement.relegated),
    )
