from __future__ import annotations

from typing import Mapping

from app.domain.league import LeagueStanding, PenaltySummary
from app.domain.seasons import SeasonVersion


def points_for_position(version: SeasonVersion, position: int) -> int:
    return int(version.points_by_position.get(int(position), 0))


def coins_for_position(version: SeasonVersion, position: int) -> int:
    return int(version.coins_by_position.get(int(position), 0))


def build_standings_from_rankings(
    *,
    matchday_id: str,
    rank_a: list[str] | tuple[str, ...],
    rank_b: list[str] | tuple[str, ...],
    version: SeasonVersion,
    division_a_id: str = "A",
    division_b_id: str = "B",
    penalties_by_trainer: Mapping[str, PenaltySummary] | None = None,
) -> tuple[LeagueStanding, ...]:
    penalties = penalties_by_trainer or {}
    standings: list[LeagueStanding] = []
    for division_id, ranking, start_position in (
        (division_a_id, tuple(rank_a), 1),
        (division_b_id, tuple(rank_b), len(rank_a) + 1),
    ):
        for idx, trainer_id in enumerate(ranking, start=1):
            position = start_position + idx - 1
            standings.append(
                LeagueStanding(
                    matchday_id=matchday_id,
                    trainer_id=str(trainer_id),
                    division_id=division_id,
                    position=position,
                    division_position=idx,
                    points_awarded=points_for_position(version, position),
                    coins_awarded=coins_for_position(version, position),
                    penalties=penalties.get(str(trainer_id), PenaltySummary()),
                )
            )
    return tuple(standings)


def sum_awards(standings: list[LeagueStanding] | tuple[LeagueStanding, ...]) -> tuple[dict[str, int], dict[str, int]]:
    points = {row.trainer_id: int(row.points_awarded) for row in standings}
    coins = {row.trainer_id: int(row.coins_awarded) for row in standings}
    return points, coins
