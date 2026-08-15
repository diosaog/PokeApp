from __future__ import annotations

from app.domain.common import epoch_to_utc_iso
from app.domain.league import MatchdaySnapshot, PenaltySummary
from app.domain.seasons import SeasonVersion
from app.domain.services.rewards import build_standings_from_rankings, sum_awards


def build_matchday_snapshot(
    *,
    snapshot_id: str,
    matchday_id: str,
    season_id: str,
    matchday_number: int,
    closed_at: str | int,
    version: SeasonVersion,
    rank_a: list[str] | tuple[str, ...],
    rank_b: list[str] | tuple[str, ...],
    division_composition: dict[str, list[str] | tuple[str, ...]],
    penalties_by_trainer: dict[str, PenaltySummary] | None = None,
    source: str = "finalize",
) -> MatchdaySnapshot:
    closed = epoch_to_utc_iso(closed_at) if isinstance(closed_at, int) else str(closed_at)
    standings = build_standings_from_rankings(
        matchday_id=matchday_id,
        rank_a=rank_a,
        rank_b=rank_b,
        version=version,
        penalties_by_trainer=penalties_by_trainer,
    )
    points, coins = sum_awards(standings)
    penalties = {row.trainer_id: row.penalties for row in standings}
    return MatchdaySnapshot(
        id=snapshot_id,
        schema_version=1,
        matchday_id=matchday_id,
        season_id=season_id,
        matchday_number=matchday_number,
        closed_at=closed,
        season_version=version,
        division_composition={
            str(key): tuple(str(value) for value in values)
            for key, values in division_composition.items()
        },
        standings=standings,
        points_awarded=points,
        coins_awarded=coins,
        penalties=penalties,
        metadata={"source": str(source or "finalize")},
    )
